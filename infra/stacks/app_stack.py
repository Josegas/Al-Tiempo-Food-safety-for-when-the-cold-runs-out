"""The product: agent on AgentCore Runtime + serverless API + reminders + web.

User -> CloudFront (web + /api/*) -> API Gateway (throttled) -> Lambda (daily cap)
     -> AgentCore Runtime (Strands agent, IAM-authenticated) -> Bedrock (Nova 2 Lite profile)
Agent -> EventBridge Scheduler (one-time, self-deleting) -> reminder Lambda -> DynamoDB (TTL) / SNS
"""

from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_bedrock as bedrock
from aws_cdk import aws_bedrockagentcore as agentcore
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_assets as s3_assets
from aws_cdk import aws_s3_deployment as s3deploy
from aws_cdk import aws_scheduler as scheduler
from aws_cdk import aws_sns as sns
from aws_cdk import aws_ssm as ssm
from constructs import Construct
from stacks import names

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build"


class AppStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        account, region = self.account, self.region
        sms_enabled = bool(self.node.try_get_context("smsEnabled"))

        # ---------------- Data: DynamoDB with TTL (personal data expires in 7 days) ----------------
        table = dynamodb.Table(
            self,
            "Table",
            table_name=names.TABLE_NAME,
            partition_key=dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="expires_at",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ---------------- Model: application inference profile (cost attribution by tag) --------
        profile = bedrock.CfnApplicationInferenceProfile(
            self,
            "ModelProfile",
            inference_profile_name="al-tiempo-nova-2-lite",
            description="Nova 2 Lite profile for Al Tiempo cost tracking",
            model_source=bedrock.CfnApplicationInferenceProfile.InferenceProfileModelSourceProperty(
                copy_from=f"arn:aws:bedrock:{region}:{account}:inference-profile/us.amazon.nova-2-lite-v1:0"
            ),
        )
        model_arn = profile.attr_inference_profile_arn

        # ---------------- Reminders: Lambda + Scheduler group + role ----------------
        reminder_fn = lambda_.Function(
            self,
            "ReminderFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(ROOT / "infra" / "lambdas" / "reminder")),
            timeout=Duration.seconds(10),
            memory_size=128,
            environment={"TABLE_NAME": table.table_name, "SMS_ENABLED": str(sms_enabled).lower()},
            log_group=logs.LogGroup(
                self,
                "ReminderLogs",
                retention=logs.RetentionDays.ONE_WEEK,
                removal_policy=RemovalPolicy.DESTROY,
            ),
        )
        table.grant_write_data(reminder_fn)
        if sms_enabled:
            reminder_fn.add_to_role_policy(
                iam.PolicyStatement(actions=["sns:Publish"], resources=["*"])  # phone numbers
            )

        scheduler.CfnScheduleGroup(self, "ScheduleGroup", name=names.SCHEDULE_GROUP)
        scheduler_role = iam.Role(
            self,
            "SchedulerRole",
            assumed_by=iam.ServicePrincipal(
                "scheduler.amazonaws.com",
                conditions={"StringEquals": {"aws:SourceAccount": account}},
            ),
        )
        reminder_fn.grant_invoke(scheduler_role)

        # ---------------- Agent: AgentCore Runtime (direct code deployment, ARM64) ----------------
        code = s3_assets.Asset(self, "AgentCode", path=str(BUILD / "agent.zip"))
        runtime_role = iam.Role(
            self,
            "RuntimeRole",
            role_name=names.RUNTIME_ROLE,
            assumed_by=iam.ServicePrincipal(
                "bedrock-agentcore.amazonaws.com",
                conditions={
                    "StringEquals": {"aws:SourceAccount": account},
                    "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account}:*"},
                },
            ),
        )
        runtime_policy = iam.Policy(
            self,
            "RuntimePolicy",
            statements=[
                iam.PolicyStatement(
                    sid="InvokeOnlyNova2Lite",
                    actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                    resources=[
                        model_arn,
                        f"arn:aws:bedrock:{region}:{account}:inference-profile/us.amazon.nova-2-lite-v1:0",
                        "arn:aws:bedrock:*::foundation-model/amazon.nova-2-lite-v1:0",
                    ],
                ),
                iam.PolicyStatement(
                    sid="RuntimeLogs",
                    actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                    resources=[
                        f"arn:aws:logs:{region}:{account}:log-group:/aws/bedrock-agentcore/runtimes/*"
                    ],
                ),
                iam.PolicyStatement(
                    sid="RuntimeLogDiscovery",
                    actions=["logs:DescribeLogStreams", "logs:DescribeLogGroups"],
                    resources=[f"arn:aws:logs:{region}:{account}:log-group:*"],
                ),
                iam.PolicyStatement(
                    sid="RuntimeTracesAndMetrics",
                    actions=[
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords",
                        "cloudwatch:PutMetricData",
                    ],
                    resources=["*"],
                    conditions=None,
                ),
                iam.PolicyStatement(
                    sid="WorkloadIdentity",
                    actions=[
                        "bedrock-agentcore:GetWorkloadAccessToken",
                        "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                        "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
                    ],
                    resources=[
                        f"arn:aws:bedrock-agentcore:{region}:{account}:workload-identity-directory/default",
                        f"arn:aws:bedrock-agentcore:{region}:{account}:workload-identity-directory/default/workload-identity/*",
                    ],
                ),
                iam.PolicyStatement(
                    sid="CreateRemindersInOurGroupOnly",
                    actions=["scheduler:CreateSchedule"],
                    resources=[
                        f"arn:aws:scheduler:{region}:{account}:schedule/{names.SCHEDULE_GROUP}/*"
                    ],
                ),
                iam.PolicyStatement(
                    sid="PassSchedulerRoleToSchedulerOnly",
                    actions=["iam:PassRole"],
                    resources=[scheduler_role.role_arn],
                    conditions={"StringEquals": {"iam:PassedToService": "scheduler.amazonaws.com"}},
                ),
            ],
        )
        runtime_role.attach_inline_policy(runtime_policy)
        code.grant_read(runtime_role)

        runtime = agentcore.CfnRuntime(
            self,
            "AgentRuntime",
            agent_runtime_name=names.RUNTIME_NAME,
            description="Al Tiempo food-safety agent (Strands Agents SDK)",
            role_arn=runtime_role.role_arn,
            agent_runtime_artifact=agentcore.CfnRuntime.AgentRuntimeArtifactProperty(
                code_configuration=agentcore.CfnRuntime.CodeConfigurationProperty(
                    code=agentcore.CfnRuntime.CodeProperty(
                        s3=agentcore.CfnRuntime.S3LocationProperty(
                            bucket=code.s3_bucket_name, prefix=code.s3_object_key
                        )
                    ),
                    runtime="PYTHON_3_12",
                    entry_point=["main.py"],
                )
            ),
            network_configuration=agentcore.CfnRuntime.NetworkConfigurationProperty(
                network_mode="PUBLIC"  # outbound internet for the forecast API; inbound needs IAM
            ),
            protocol_configuration="HTTP",
            lifecycle_configuration=agentcore.CfnRuntime.LifecycleConfigurationProperty(
                idle_runtime_session_timeout=300, max_lifetime=3600
            ),
            environment_variables={
                "MODEL_ID": model_arn,
                "DEMO_MODE": "true",  # default for the public demo; the web can switch to live
                "ALLOW_UNVERIFIED_RULES": "false",
                "DEFAULT_TIMEZONE": "America/Mazatlan",
                "REMINDER_LAMBDA_ARN": reminder_fn.function_arn,
                "SCHEDULER_ROLE_ARN": scheduler_role.role_arn,
                "SCHEDULE_GROUP": names.SCHEDULE_GROUP,
                "CODE_SHA": code.asset_hash[:12],
            },
            tags={"project": names.PROJECT},
        )
        runtime.node.add_dependency(runtime_policy)
        runtime.node.add_dependency(runtime_role)
        runtime_arn = runtime.attr_agent_runtime_arn

        # ---------------- API: Lambda (daily cap) + HTTP API (throttled) ----------------
        api_role = iam.Role(
            self,
            "ApiRole",
            role_name=names.API_ROLE,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )
        api_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock-agentcore:InvokeAgentRuntime"],
                resources=[runtime_arn, f"{runtime_arn}/*"],
            )
        )
        api_role.add_to_policy(
            iam.PolicyStatement(actions=["polly:SynthesizeSpeech"], resources=["*"])
        )
        boto_layer = lambda_.LayerVersion(
            self,
            "Boto3Layer",
            code=lambda_.Code.from_asset(str(BUILD / "boto3_layer")),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            compatible_architectures=[lambda_.Architecture.ARM_64],
            description="Recent boto3 with the bedrock-agentcore client",
        )
        api_fn = lambda_.Function(
            self,
            "ApiFn",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            handler="handler.handler",
            code=lambda_.Code.from_asset(str(ROOT / "infra" / "lambdas" / "api")),
            layers=[boto_layer],
            role=api_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            reserved_concurrent_executions=None,
            environment={
                "TABLE_NAME": table.table_name,
                "RUNTIME_ARN": runtime_arn,
                "DAILY_CAP": str(self.node.try_get_context("dailyChatCap") or 500),
                "POLLY_ENGINE": "standard",
            },
            log_group=logs.LogGroup(
                self,
                "ApiLogs",
                retention=logs.RetentionDays.ONE_WEEK,
                removal_policy=RemovalPolicy.DESTROY,
            ),
        )
        table.grant_read_write_data(api_fn)

        http_api = apigw.HttpApi(
            self, "HttpApi", api_name="al-tiempo-api", create_default_stage=False
        )
        apigw.HttpStage(
            self,
            "DefaultStage",
            http_api=http_api,
            stage_name="$default",
            auto_deploy=True,
            throttle=apigw.ThrottleSettings(rate_limit=3, burst_limit=10),
        )
        integration = integrations.HttpLambdaIntegration("ApiIntegration", api_fn)
        for method, path in [
            (apigw.HttpMethod.POST, "/api/chat"),
            (apigw.HttpMethod.GET, "/api/reminders"),
            (apigw.HttpMethod.POST, "/api/voice"),
            (apigw.HttpMethod.GET, "/api/health"),
        ]:
            http_api.add_routes(path=path, methods=[method], integration=integration)

        # ---------------- Web: private S3 + CloudFront (OAC), API on the same domain ----------
        site_bucket = s3.Bucket(
            self,
            "SiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        api_origin = origins.HttpOrigin(
            f"{http_api.api_id}.execute-api.{region}.amazonaws.com",
            protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
        )
        distribution = cloudfront.Distribution(
            self,
            "Site",
            comment="Al Tiempo demo",
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                response_headers_policy=cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS,
            ),
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=api_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                )
            },
        )
        s3deploy.BucketDeployment(
            self,
            "DeploySite",
            sources=[s3deploy.Source.asset(str(ROOT / "web"))],
            destination_bucket=site_bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )

        # ---------------- Observability: dashboard + alarms (email via access stack) ----------
        topic = sns.Topic.from_topic_arn(
            self,
            "AlarmTopic",
            ssm.StringParameter.value_for_string_parameter(self, names.ALARM_TOPIC_PARAM),
        )
        alarms = [
            cw.Alarm(
                self,
                "ApiErrors",
                alarm_description="API Lambda errors",
                metric=api_fn.metric_errors(period=Duration.minutes(5)),
                threshold=3,
                evaluation_periods=1,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            ),
            cw.Alarm(
                self,
                "ApiSlow",
                alarm_description="API p90 latency above 20 s",
                metric=api_fn.metric_duration(period=Duration.minutes(5), statistic="p90"),
                threshold=20_000,
                evaluation_periods=2,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            ),
            cw.Alarm(
                self,
                "ReminderErrors",
                alarm_description="Reminder delivery errors",
                metric=reminder_fn.metric_errors(period=Duration.minutes(5)),
                threshold=1,
                evaluation_periods=1,
                treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
            ),
        ]
        for alarm in alarms:
            alarm.add_alarm_action(cw_actions.SnsAction(topic))

        dashboard = cw.Dashboard(self, "Dashboard", dashboard_name="al-tiempo")
        dashboard.add_widgets(
            cw.GraphWidget(
                title="API requests / errors",
                left=[api_fn.metric_invocations(), api_fn.metric_errors()],
            ),
            cw.GraphWidget(
                title="API latency (p50 / p90, ms)",
                left=[
                    api_fn.metric_duration(statistic="p50"),
                    api_fn.metric_duration(statistic="p90"),
                ],
            ),
            cw.GraphWidget(
                title="Reminders delivered / errors",
                left=[reminder_fn.metric_invocations(), reminder_fn.metric_errors()],
            ),
            cw.GraphWidget(
                title="Bedrock tokens (Nova 2 Lite profile)",
                left=[
                    cw.Metric(
                        namespace="AWS/Bedrock",
                        metric_name=name,
                        dimensions_map={"ModelId": profile.attr_inference_profile_id},
                        statistic="Sum",
                    )
                    for name in ("InputTokenCount", "OutputTokenCount")
                ],
            ),
        )

        # ---------------- Kill switch: hard stop if the project budget is exceeded ------------
        # AWS Budgets attaches a DENY policy to the runtime and API roles at 100% of the budget
        # (budget "al-tiempo-monthly" lives in the access stack). Detach it to resume.
        kill_switch = iam.ManagedPolicy(
            self,
            "KillSwitchPolicy",
            managed_policy_name="al-tiempo-kill-switch",
            description="Attached automatically by AWS Budgets when the project exceeds its budget.",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.DENY,
                    actions=[
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream",
                        "bedrock-agentcore:InvokeAgentRuntime",
                        "polly:SynthesizeSpeech",
                    ],
                    resources=["*"],
                )
            ],
        )
        budget_action_role = iam.Role(
            self,
            "BudgetActionRole",
            assumed_by=iam.ServicePrincipal(
                "budgets.amazonaws.com",
                conditions={"StringEquals": {"aws:SourceAccount": account}},
            ),
        )
        budget_action_role.add_to_policy(
            iam.PolicyStatement(
                actions=["iam:AttachRolePolicy", "iam:DetachRolePolicy"],
                resources=[runtime_role.role_arn, api_role.role_arn],
                conditions={"ArnEquals": {"iam:PolicyARN": kill_switch.managed_policy_arn}},
            )
        )
        action = budgets.CfnBudgetsAction(
            self,
            "KillSwitch",
            budget_name="al-tiempo-monthly",
            action_type="APPLY_IAM_POLICY",
            action_threshold=budgets.CfnBudgetsAction.ActionThresholdProperty(
                type="PERCENTAGE", value=100
            ),
            approval_model="AUTOMATIC",
            execution_role_arn=budget_action_role.role_arn,
            notification_type="ACTUAL",
            definition=budgets.CfnBudgetsAction.DefinitionProperty(
                iam_action_definition=budgets.CfnBudgetsAction.IamActionDefinitionProperty(
                    policy_arn=kill_switch.managed_policy_arn,
                    roles=[runtime_role.role_name, api_role.role_name],
                )
            ),
            subscribers=[
                budgets.CfnBudgetsAction.SubscriberProperty(type="SNS", address=topic.topic_arn)
            ],
        )
        action.node.add_dependency(budget_action_role)

        CfnOutput(self, "SiteUrl", value=f"https://{distribution.distribution_domain_name}")
        CfnOutput(self, "ApiUrl", value=http_api.api_endpoint)
        CfnOutput(self, "RuntimeArn", value=runtime_arn)
        CfnOutput(self, "ModelProfileArn", value=model_arn)
        CfnOutput(self, "TableName", value=table.table_name)

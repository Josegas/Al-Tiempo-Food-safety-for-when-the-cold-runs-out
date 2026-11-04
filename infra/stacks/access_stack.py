"""Who can touch the project, and how much it may cost.

- IAM user `al-tiempo-dev` in group `al-tiempo-developers`: least-privilege day-to-day access.
  It deploys ONLY through the CDK bootstrap roles (every change goes through CloudFormation).
- GitHub Actions deploy role via OIDC: no long-lived keys in GitHub; only `main` can deploy.
- Budget for resources tagged project=al-tiempo with email alerts. (The kill switch that acts on
  this budget lives in the app stack, next to the roles it blocks.)
- SNS topic for CloudWatch alarms (email), published in SSM for the app stack.
"""

from aws_cdk import Stack
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_sns as sns
from aws_cdk import aws_ssm as ssm
from constructs import Construct
from stacks import names


class AccessStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, alert_email: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        account, region = self.account, self.region
        cdk_roles = f"arn:aws:iam::{account}:role/cdk-{names.CDK_QUALIFIER}-*-{account}-{region}"
        runtime_arn = f"arn:aws:bedrock-agentcore:{region}:{account}:runtime/{names.RUNTIME_NAME}*"

        # ---------------- Developer access (least privilege) ----------------
        dev_policy = iam.ManagedPolicy(
            self,
            "DeveloperPolicy",
            managed_policy_name="al-tiempo-developer",
            description="Al Tiempo developer: deploy via CDK roles, test the agent, read logs/costs.",
            statements=[
                iam.PolicyStatement(
                    sid="DeployThroughCdkRolesOnly",
                    actions=["sts:AssumeRole"],
                    resources=[cdk_roles],
                ),
                iam.PolicyStatement(
                    sid="ReadStacks",
                    actions=[
                        "cloudformation:DescribeStacks",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:GetTemplate",
                        "cloudformation:ListStackResources",
                    ],
                    resources=[
                        f"arn:aws:cloudformation:{region}:{account}:stack/AlTiempo*/*",
                        f"arn:aws:cloudformation:{region}:{account}:stack/CDKToolkit/*",
                    ],
                ),
                iam.PolicyStatement(
                    sid="ReadBootstrapVersion",
                    actions=["ssm:GetParameter"],
                    resources=[
                        f"arn:aws:ssm:{region}:{account}:parameter/cdk-bootstrap/{names.CDK_QUALIFIER}/version"
                    ],
                ),
                iam.PolicyStatement(
                    sid="InvokeNova2LiteForLocalTestsAndEvals",
                    actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                    resources=[
                        f"arn:aws:bedrock:{region}:{account}:application-inference-profile/*",
                        f"arn:aws:bedrock:{region}:{account}:inference-profile/us.amazon.nova-2-lite-v1:0",
                        "arn:aws:bedrock:*::foundation-model/amazon.nova-2-lite-v1:0",
                    ],
                ),
                iam.PolicyStatement(
                    sid="ReadInferenceProfiles",
                    actions=["bedrock:GetInferenceProfile", "bedrock:ListInferenceProfiles"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    sid="TestDeployedAgent",
                    actions=[
                        "bedrock-agentcore:InvokeAgentRuntime",
                        "bedrock-agentcore:GetAgentRuntime",
                        "bedrock-agentcore:ListAgentRuntimeEndpoints",
                    ],
                    resources=[runtime_arn, f"{runtime_arn}/*"],
                ),
                iam.PolicyStatement(
                    sid="ReadProjectLogs",
                    actions=[
                        "logs:DescribeLogStreams",
                        "logs:GetLogEvents",
                        "logs:FilterLogEvents",
                        "logs:StartQuery",
                    ],
                    resources=[
                        f"arn:aws:logs:{region}:{account}:log-group:/aws/lambda/AlTiempo*",
                        f"arn:aws:logs:{region}:{account}:log-group:/aws/bedrock-agentcore/runtimes/{names.RUNTIME_NAME}*",
                    ],
                ),
                iam.PolicyStatement(
                    sid="LogsQueryAndListing",
                    actions=["logs:DescribeLogGroups", "logs:GetQueryResults", "logs:StopQuery"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    sid="DebugProjectData",
                    actions=["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"],
                    resources=[f"arn:aws:dynamodb:{region}:{account}:table/{names.TABLE_NAME}"],
                ),
                iam.PolicyStatement(
                    sid="DebugReminders",
                    actions=["scheduler:ListSchedules", "scheduler:GetSchedule"],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    sid="MeasureCostsAndMetrics",
                    actions=[
                        "ce:GetCostAndUsage",
                        "budgets:ViewBudget",
                        "pricing:GetProducts",
                        "cloudwatch:GetMetricData",
                        "cloudwatch:ListMetrics",
                        "cloudwatch:GetDashboard",
                    ],
                    resources=["*"],
                ),
            ],
        )
        group = iam.Group(
            self, "Developers", group_name="al-tiempo-developers", managed_policies=[dev_policy]
        )
        iam.User(self, "DevUser", user_name="al-tiempo-dev", groups=[group])

        # ---------------- GitHub Actions: OIDC, no stored keys ----------------
        # GitHub sends an *immutable* subject (owner and repo IDs), not just "repo:owner/name":
        # gh api repos/OWNER/REPO/actions/oidc/customization/sub -> sub_claim_prefix.
        # It survives renames and blocks a re-created repo with the same name from deploying.
        sub_prefix = self.node.try_get_context("githubOidcSubPrefix") or (
            f"repo:{self.node.try_get_context('githubRepo')}"
        )
        provider = iam.OpenIdConnectProvider.from_open_id_connect_provider_arn(
            self,
            "GitHubOidc",
            f"arn:aws:iam::{account}:oidc-provider/token.actions.githubusercontent.com",
        )  # already exists in the account (one per URL)
        deploy_role = iam.Role(
            self,
            "GitHubDeployRole",
            role_name="al-tiempo-github-deploy",
            description="Assumed by GitHub Actions (main branch only) to deploy AlTiempoApp.",
            max_session_duration=None,
            assumed_by=iam.WebIdentityPrincipal(
                provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                        "token.actions.githubusercontent.com:sub": f"{sub_prefix}:ref:refs/heads/main",
                    }
                },
            ),
        )
        deploy_role.add_to_policy(
            iam.PolicyStatement(actions=["sts:AssumeRole"], resources=[cdk_roles])
        )
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudformation:DescribeStacks"],
                resources=[f"arn:aws:cloudformation:{region}:{account}:stack/AlTiempoApp/*"],
            )
        )

        # ---------------- Alarms topic (email) ----------------
        topic = sns.Topic(self, "AlarmTopic", topic_name="al-tiempo-alarms")
        sns.Subscription(  # fixed id: the email never appears in logical IDs
            self, "AlarmEmail", topic=topic, endpoint=alert_email,
            protocol=sns.SubscriptionProtocol.EMAIL,
        )  # fmt: skip
        topic.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowBudgetsToNotify",
                principals=[iam.ServicePrincipal("budgets.amazonaws.com")],
                actions=["SNS:Publish"],
                resources=[topic.topic_arn],
                conditions={"StringEquals": {"aws:SourceAccount": account}},
            )
        )
        ssm.StringParameter(
            self,
            "AlarmTopicParam",
            parameter_name=names.ALARM_TOPIC_PARAM,
            string_value=topic.topic_arn,
        )

        # ---------------- Project budget (email alerts) ----------------
        limit = float(self.node.try_get_context("monthlyBudgetUsd") or 5)
        budget_name = "al-tiempo-monthly"
        email = [
            budgets.CfnBudget.SubscriberProperty(subscription_type="EMAIL", address=alert_email)
        ]

        def notify(kind: str, pct: float) -> budgets.CfnBudget.NotificationWithSubscribersProperty:
            return budgets.CfnBudget.NotificationWithSubscribersProperty(
                notification=budgets.CfnBudget.NotificationProperty(
                    notification_type=kind,
                    comparison_operator="GREATER_THAN",
                    threshold=pct,
                    threshold_type="PERCENTAGE",
                ),
                subscribers=email,
            )

        budgets.CfnBudget(
            self,
            "MonthlyBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name=budget_name,
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(amount=limit, unit="USD"),
                cost_filters={"TagKeyValue": [f"user:project${names.PROJECT}"]},
                # Gross usage (before credits), like the other project budgets in this account.
                cost_types=budgets.CfnBudget.CostTypesProperty(include_credit=False),
            ),
            notifications_with_subscribers=[
                notify("ACTUAL", 50),
                notify("ACTUAL", 80),
                notify("ACTUAL", 100),
                notify("FORECASTED", 100),
            ],
        )

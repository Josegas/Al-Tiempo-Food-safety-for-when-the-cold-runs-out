#!/usr/bin/env python3
"""CDK app for Al Tiempo.

Stacks:
  AlTiempoAccess  people & money: dev IAM user/group (least privilege), GitHub OIDC deploy role,
                  budget + kill switch, alarm topic. Deployed once by an admin; needs ALERT_EMAIL.
  AlTiempoApp     the product: AgentCore Runtime, Lambdas, API, DynamoDB, Scheduler, web.
                  Deployed by the dev user or by GitHub Actions (OIDC, no stored keys).
"""

import os

import aws_cdk as cdk
from stacks.access_stack import AccessStack
from stacks.app_stack import AppStack

app = cdk.App()
env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION", "us-east-1")
)

cdk.Tags.of(app).add("project", "al-tiempo")  # cost allocation tag -> project budget

alert_email = os.getenv("ALERT_EMAIL")
if alert_email:  # only when an admin deploys the access stack (never in CI)
    AccessStack(app, "AlTiempoAccess", env=env, alert_email=alert_email)

AppStack(app, "AlTiempoApp", env=env)

app.synth()

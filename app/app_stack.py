from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_timestream as timestream,
    Duration,
    RemovalPolicy,
    SecretValue,
    aws_lambda_event_sources as lambda_event_sources,
)
from constructs import Construct
import os
from dotenv import load_dotenv
import enviro_lambda.lambda_function as lf

load_dotenv()


class EnviroLoggerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # IAM
        # IAM User with AdministratorAccess and IAMUserChangePassword
        admin_user = iam.User(
            self,
            "mrerzincan",
            password=SecretValue.plain_text(os.getenv("IAM_ADMIN_USER_PW")),
            password_reset_required=True,  # Users with AdministratorAccess should have password reset required
        )
        admin_user.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
        )
        admin_user.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("IAMUserChangePassword")
        )

        # IAM Group for S3, Timestream, Lambda access
        enviro_group = iam.Group(self, "enviro")

        # IAM Policies for S3, Timestream, Lambda
        s3_policy = iam.Policy(
            self,
            "S3Policy",
            statements=[iam.PolicyStatement(actions=["s3:*"], resources=["*"])],
        )
        object_lambda_policy = iam.Policy(
            self,
            "ObjectLambdaPolicy",
            statements=[
                iam.PolicyStatement(actions=["s3-object-lambda:*"], resources=["*"])
            ],
        )
        timestream_policy = iam.Policy(
            self,
            "TimestreamPolicy",
            statements=[iam.PolicyStatement(actions=["timestream:*"], resources=["*"])],
        )
        lambda_policy = iam.Policy(
            self,
            "LambdaPolicy",
            statements=[iam.PolicyStatement(actions=["lambda:*"], resources=["*"])],
        )

        # Attach policies to group
        enviro_group.add_managed_policy(s3_policy)
        enviro_group.add_managed_policy(object_lambda_policy)
        enviro_group.add_managed_policy(timestream_policy)
        enviro_group.add_managed_policy(lambda_policy)

        # IAM Users added to the IAM Group
        iam_user1 = iam.User(
            self,
            "mrerzincan_enviro",
            password=SecretValue.plain_text(os.getenv("IAM_USER_MRERZINCAN_ENVIRO_PW")),
        )
        iam_user2 = iam.User(
            self,
            "hakan_enviro",
            password=SecretValue.plain_text(os.getenv("IAM_USER_HAKAN_ENVIRO_PW")),
        )

        enviro_group.add_user(iam_user1)
        enviro_group.add_user(iam_user2)

        # Define an S3 bucket
        my_enviro_bucket = s3.Bucket(
            self,
            "myenvirobucket",
            versioned=False,  # Disable versioning (optional)
            removal_policy=RemovalPolicy.DESTROY,  # This will delete the bucket when the stack is deleted (use with caution)
        )

        # S3 bucket for error logs
        timestream_error_logs_bucket = s3.Bucket(
            self, "mytimestreamerrorlogs", removal_policy=RemovalPolicy.DESTROY
        )

        # Timestream database
        timestream_database = timestream.CfnDatabase(
            self, "MyEnviroTimestreamDatabase", database_name="enviroDB-CDK"
        )

        # Timestream table
        timestream_table = timestream.CfnTable(
            self,
            "MyEnviroTimestreamTable",
            database_name=timestream_database.database_name,
            table_name="enviroTable-CDK",
        )

        # Add the dependency
        timestream_table.add_depends_on(timestream_database)

        # IAM role for Lambda to write to Timestream
        timestream_write_role = iam.Role(
            self,
            "TimestreamWriteRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        timestream_write_role.add_to_policy(
            iam.PolicyStatement(
                actions=["timestream:WriteRecords"],
                resources=[timestream_table.attr_arn],
            )
        )

        # Lambda function
        lambda_function = _lambda.Function(
            self,
            "enviroLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="enviro_lambda.lambda_function.lambda_handler",  # Adjust the import path
            code=_lambda.Code.from_asset(
                "enviro_lambda"
            ),  # Path to your Lambda function code
            environment={
                "TIMESTREAM_DATABASE_NAME": "enviroDB-CDK",
                "ERROR_LOGS_BUCKET_NAME": timestream_error_logs_bucket.bucket_name,
            },
            timeout=Duration.seconds(30),
        )

        # Grant Lambda permissions to read from data bucket
        my_enviro_bucket.grant_read(lambda_function)

        # Grant Lambda permission to assume the IAM role
        lambda_function.role.add_to_policy(
            iam.PolicyStatement(
                actions=["sts:AssumeRole"], resources=[timestream_write_role.role_arn]
            )
        )

        # Grant S3 bucket permission for error logs
        timestream_error_logs_bucket.grant_write(lambda_function)

        # Configure Lambda function to trigger on S3 object creation events
        lambda_function.add_event_source(
            lambda_event_sources.S3EventSource(
                my_enviro_bucket, events=[s3.EventType.OBJECT_CREATED]
            )
        )

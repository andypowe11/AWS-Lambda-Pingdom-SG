# AWS Lambda function to whitelist the Pingdom probe IP addresses

[Pingdom](https://www.pingdom.com/) is an online service that regularly monitors website
uptime and performance.

In cases where the website you want to monitor is not publicly accessible, you will need to
whitelist all of the
[Pingdom probe IP addresses](https://help.pingdom.com/hc/en-us/articles/203682601-How-to-get-all-Pingdom-probes-public-IP-addresses)
in order that monitoring can take place.

This AWS Lambda function updates a set of security groups that collectively whitelist all the
Pingdom probe IP addresses, allowing inbound traffic on ports 80 and 443.

To function properly, the Lamdbda function should be called regularly (at least once per day).

## Usage

### Create a set of security groups

Create a set of AWS security groups, using names of the form 'pingdom1', 'pingdom2', etc.
Set a **Name** tag, with the value set to the name, and an **AutoUpdate** tag,
with the value set to 'true'.

There are currently around 70 Pingdom probe IP addresses and each requires 2 security
group rules - one for port 80 and one for port 443.
That's around 140 rules.
Each security group is limited to 50 rules by default, so unless you get the limit
raised, you'll need to create 3 security groups.

### Create an IAM policy and execution role for the Lambda function

You will create the Lambda execution role that determines the AWS service
calls that the function is authorized to complete.

Before doing so, you need to create an IAM policy that you will attach to the role.

1. In the IAM console, click **Policies** > **Create Policy** > **Select** (next to **Create Your Own Policy**).
2. Then supply a name for your policy, and copy and paste the following policy
into the **Policy Document** box:

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress"
      ],
      "Resource": "*"
    }
  ]
}
```

### Create an execution role

Now that you have created your policy, you can create your Lambda execution role using that policy:

1. In the IAM console, click **Roles** > **Create New Role**, and then name your role.
2. To select a role type, select **AWS Service Roles** > **AWS Lambda**.
3. Attach the policy you just created.
4. After confirming your selections, click **Create Role**.

### Create your Lambda function

Now that you have created your Lambda execution role, you can create your Lambda function:

1. Go to the Lambda console and select **Create a Lambda function**.
2. Give your Lambda function a name and description, and select **Python 2.7** from the Runtime menu.
3. Paste the code from `lambda-pingdom-sg.py`.
4. Below the code window for Lambda function handler and role, select the execution role you created earlier.
5. Under **Advanced settings**, increase the **Timeout** to 15 seconds.
6. Finally, click **Next**.
7. After confirming your settings are correct, click **Create function**.

Modify the following variables in `lambda-pingdom-sg.py` as necessary:

```
# Ports that need inbound permissions from the Pingdom probes
INGRESS_PORTS = [ 80, 443 ]
# Tags which identify the security groups you want to update
SECURITY_GROUP_TAGS = { 'Name': 'pingdom*', 'AutoUpdate': 'true' }
# Limit on inbound rules per Security Group (default: 50)
RULES_PER_SG = 50
# Region to search for Security Groups 
AWS_REGION = "us-east-1"
```

## Running your Lambda function

Configure a **Scheduled Event** (under **Event sources**) to run the Lambda function on
(at least) a daily basis.

Apply the resulting security groups to any resources (instances or ELBs) that you want to be accessible
to the Pingdom probes.

## Notes

This Lambda function and associated instructions are heavily based on
https://blogs.aws.amazon.com/security/post/Tx1LPI2H6Q6S5KC/How-to-Automatically-Update-Your-Security-Groups-for-Amazon-CloudFront-and-AWS-W

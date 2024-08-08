import os
import boto3
import constants
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText


def send_email(subject, recipient, body, body_type, attachment_path, attachment_name):
    client = boto3.client(
        'ses',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=constants.SES_REGION
    )

    # Create a multipart message
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = constants.SENDER
    msg['To'] = 'noreply@innovercapital.com'

    # Set message body
    body = MIMEText(body, body_type)
    msg.attach(body)

    # Add attachment
    if attachment_path:
        with open(attachment_path, 'rb') as attachment:
            part = MIMEApplication(attachment.read(), Name=f'{attachment_name}')
            part['Content-Disposition'] = f'attachment; filename="{attachment_name}"'
            msg.attach(part)

    try:
        # Provide the contents of the email.
        response = client.send_raw_email(
            Source=constants.SENDER,
            Destinations=recipient,
            RawMessage={
                'Data': msg.as_string(),
            }
        )
    except Exception as e:
        print(f"Error sending email: {e}")
    else:
        print(f"Email sent! Message ID:", response['MessageId'])
import boto3
import os

dynamodb = boto3.resource(
        'dynamodb',
        aws_access_key_id='AKIATCKASWVWAQETYRGY',
        aws_secret_access_key='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',
        region_name='ap-southeast-2'
    )
table = dynamodb.Table('trade_data')


def get_previous_total(trade_name):
    response = table.get_item(
        Key={
            'trade_name': trade_name
        }
    )
    item = response.get('Item', {})
    prev_value = item['prev_value']
    print(f"Previous value of {trade_name} is: {prev_value}")
    return prev_value


def update_previous_total(trade_name, curr):
    update_response = table.update_item(
        Key={
            'trade_name': trade_name
        },
        UpdateExpression='SET prev_value = :val',
        ExpressionAttributeValues={
            ':val': curr
        },
        ReturnValues="UPDATED_NEW"
    )
    print(f"Updated {trade_name}: {update_response}")


def get_previous_t1_unconfirmed(date):
    response = table.get_item(
        Key={
            'trade_name': date
        }
    )
    item = response.get('Item', {})
    if not item:
        return {}
    prev_value = item['prev_value']
    print("Previous value of t+1 trade is: ", prev_value)
    return prev_value


def update_t1_unconfirmed(date, trade_to_amount_dict):
    update_response = table.update_item(
        Key={
            'trade_name': date
        },
        UpdateExpression='SET prev_value = :val',
        ExpressionAttributeValues={
            ':val': trade_to_amount_dict
        },
        ReturnValues="UPDATED_NEW"
    )
    print("Updated t+1 trade:", update_response)

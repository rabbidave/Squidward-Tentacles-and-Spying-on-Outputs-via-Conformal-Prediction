# My thanks to the open-source community; LLMs brought about a GNU revival
# My thanks to Arize AI in particular; y'all inspired this and other utilities with an awesome observability platform & sessions
# Note: This Lambda has a timeout to ensure it's spun down gracefully; manage your Lambda with Provisioned Concurrency to ensure SQS messages don't get missed
# Note: This Lambda has a non-trivial computational cost and is intended to monitor and append messages based on the non-conformity to a representative distribution of outputs
# i.e. it's used to validate stuff like externally facing LLMs using an objective measure of "confidence" given a specific output


import pandas as pd
import boto3
import time
import json
import os
from botocore.exceptions import ClientError
import datetime
import logging
import random
from transformers import AutoTokenizer, AutoModelForCausalLM


# Define constants
CONFIDENCE_THRESHOLD_HIGH = 0.99
CONFIDENCE_THRESHOLD_LOW = 0.95
SQS_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/MyQueue'
SAFE_SQS_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/MyFirstQueue'
STANDARD_SQS_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/MySecondQueue'
LOW_CONFIDENCE_SQS_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123456789012/MyThirdQueue'
S3_BUCKET_NAME = 'my-bucket'
BASELINE_LOG_LIKELIHOODS_FILE_KEY = 'baseline_log_likelihoods.parquet'
RETRY_COUNT = 3  # Define a suitable retry count
LANGUAGE_MODEL = 'bert-base-uncased'  # Specify the language model to use

# Initialize boto3 clients
s3 = boto3.client('s3')
sqs = boto3.client('sqs')

# Initialize language model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(LANGUAGE_MODEL)

model = AutoModelForCausalLM.from_pretrained(LANGUAGE_MODEL)


# Setup logging
logging.basicConfig(level=logging.INFO)

# Load the baseline log-likelihoods from S3
try:
    obj = s3.get_object(Bucket=S3_BUCKET_NAME, Key=BASELINE_LOG_LIKELIHOODS_FILE_KEY)
    baseline_log_likelihoods = pd.read_parquet(obj['Body'])
except ClientError as e:
    logging.error(f'Error loading baseline log-likelihoods: {e}', exc_info=True)
    raise

def compute_log_likelihood(text):
    try:
        inputs = tokenizer(text, return_tensors='pt')
        outputs = model(inputs, labels=inputs)
        return -outputs.loss.item()
    except Exception as e:
        logging.error(f'Error computing log-likelihood: {e}', exc_info=True)
        raise

def compute_p_value(log_likelihood):
    try:
        return ((baseline_log_likelihoods > log_likelihood).sum() + 0.5 * (baseline_log_likelihoods == log_likelihood).sum()) / len(baseline_log_likelihoods)
    except Exception as e:
        logging.error(f'Error computing p-value: {e}', exc_info=True)
        raise

def send_message_to_sqs(df, queue_url):
    try:
        message = {
            'MessageBody': df.to_json(),
            'QueueUrl': queue_url
        }
        sqs.send_message(**message)
    except Exception as e:
        logging.error(f"Error sending message: {e}", exc_info=True)
        raise

def process_data(df):
    try:
        log_likelihood = compute_log_likelihood(df['text'])
        p_value = compute_p_value(log_likelihood)
        if p_value >= CONFIDENCE_THRESHOLD_HIGH:
            send_message_to_sqs(df["message"], SAFE_SQS_QUEUE_URL)
        elif CONFIDENCE_THRESHOLD_LOW <= p_value < CONFIDENCE_THRESHOLD_HIGH:
            df["message"] = df["message"] + " Note: this message achieved a confidence interval of 95% via conformal prediction; meaning there is still a 1/20 chance of error."
            send_message_to_sqs(df["message"], STANDARD_SQS_QUEUE_URL)
        else:
            df["message"] = df["message"] + " Warning: this message achieved a confidence interval of below 95% using conformal prediction; meaning there is a greater than 1/20 chance of error. Use this output with caution."
            send_message_to_sqs(df["message"], LOW_CONFIDENCE_SQS_QUEUE_URL)
    except Exception as e:
        logging.error(f'Error processing data: {e}', exc_info=True)
        raise

def receive_message(retry_count=5):  # Set a default retry count; also accepts parameters
    while retry_count > 0:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                AttributeNames=['All'],
                MaxNumberOfMessages=10,
                MessageAttributeNames=['All'],
                VisibilityTimeout=60,
                WaitTimeSeconds=20
            )
            return response
        except ClientError as e:
            logging.error(f'Error receiving message: {e}', exc_info=True)
            time.sleep((2 ** retry_count) + random.uniform(0, 1))  # Exponential backoff
            retry_count -= 1
    raise Exception("Exceeded maximum retry attempts for receiving message")


def lambda_handler(event, context):
    start_time = time.time()

    while True:
        # Check if 10 minutes have passed
        if time.time() - start_time > 600:
            break

        try:
            response = receive_message()

            if 'Messages' in response:
                for message in response['Messages']:
                    receipt_handle = message['ReceiptHandle']

                    try:
                        body = json.loads(message['Body'])
                        df = pd.DataFrame(body)

                        process_data(df)

                        # Delete message after successful processing
                        sqs.delete_message(
                            QueueUrl=SQS_QUEUE_URL,
                            ReceiptHandle=receipt_handle
                        )
                    except Exception as e:
                        logging.error(f'Error processing message: {e}', exc_info=True)
                        raise
            else:
                # No more messages in the queue, terminate the function
                break
        except ClientError as e:
            logging.error(f'Error receiving message: {e}', exc_info=True)
            time.sleep((2 ** RETRY_COUNT) + random.uniform(0, 1))  # Exponential backoff
            RETRY_COUNT -= 1
            if RETRY_COUNT == 0:

                raise




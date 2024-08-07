#
#
#

import boto3
import logging
import requests
import gzip
from shared import helpers
from bibliovault_shared import record_handling

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def process(bucket, key):

    logger.info( "EVENT: " + bucket + "/" + key )

    s3 = boto3.resource('s3')

    # download the file
    logger.info(" downloading s3://" + bucket + "/" + key )
    response = s3.Object(bucket, key).get()
    buf = response['Body'].read()
    logger.info("downloaded, size is : " + str(len(buf)))

    try : 
        # do the processing
        num_read, num_processed = record_handling.process_file_as_string(buf)

        if ( num_read > 0 and num_read == num_processed):
            # all is well
            ret = None
        else :
            ret = { 'num_read': str(num_read),
                    'num_processed' : str(num_processed) }
   
    except Exception  as e:
        logger.exception()
        ret = { 'exception': str(e) }
    
    finally: 
        return ret

def get_presigned_url_from_url(url):
    # Initialize a session using Amazon S3
    s3_client = boto3.client('s3')

    url_parts = helpers.string_after(url, "https://").split('.s3.amazonaws.com/') 
    bucket = url_parts[0]
    key = url_parts[1]
    
    # Generate a presigned URL for the S3 object
    presigned_url = s3_client.generate_presigned_url('get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=3600)
    
    logger.info("presigned url = " + presigned_url)
    return (presigned_url)


def readfile(filename):
    """
    This is the main loop receives a filename (or url) containing bibliovault metadata
    It reads the data, processes it and sends it to the opensearch index.
    It is separated out from the top-level lambda function the processing can also be started from the command line
    """
    
    logger.info("Starting BiblioVault to EMMA transfer service PST " + helpers.get_today_iso8601_datetime_pst())
        
    logger.info('Start Running')
    
    # Read the contents of the file or url into file_contents          
    if (filename.startswith('http://') or filename.startswith('https://')):
        if ("s3.amazonaws.com" in filename) :
            filename = get_presigned_url_from_url(filename)
        response = requests.get(filename)
        # Raise an exception if the request was unsuccessful
        response.raise_for_status()
        # Use the content of the response as you would with a file
        file_contents = response.content.decode('utf-8')  # assuming the file is in UTF-8 encoding
        logger.info("downloaded, size is : " + str(len(file_contents)))
    else:
        if filename.endswith('.gz'):
            my_open = gzip.open
        else:
            my_open = open    
        with my_open(filename, "r", encoding='utf-8') as file:
            file_contents = file.read()
        logger.info("downloaded, size is : " + str(len(file_contents)))

    try : 
        # Read the contents of the file            
       
        num_read, num_processed = record_handling.process_file_as_string(file_contents)

        if ( num_read > 0 and num_read == num_processed):
            # all is well
            logger.info("Finished load of file "+ filename + ", total loaded " + str(num_processed))
            ret = None
        else :
            ret = { 'num_read': str(num_read),
                    'num_processed' : str(num_processed) }
   
    except Exception  as e:
        logger.exception()
        ret = { 'exception': str(e) }
    
    finally: 
        return ret

#
# end of file
#

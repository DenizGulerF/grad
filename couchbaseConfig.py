from datetime import timedelta, datetime
import uuid
import json
# needed for any cluster connection
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
# needed for options -- cluster, timeout, SQL++ (N1QL) query, etc.
from couchbase.options import (ClusterOptions, ClusterTimeoutOptions, QueryOptions)
from couchbase.exceptions import DocumentNotFoundException, DocumentExistsException

def get_connection():
    endpoint = "couchbases://cb.sj1-9wzvlo8tmof.cloud.couchbase.com"
    username = "grad-app"
    password = "Grad1234//"
    bucket_name = "Users"
    cluster_name = "grad"
    auth = PasswordAuthenticator(username, password)
    options = ClusterOptions(auth)
    options.apply_profile("wan_development")  # Note: profile names are typically lowercase
    try:
        cluster = Cluster(endpoint, options)
        print("Cluster connected successfully!")
        
        # Get bucket reference
        bucket = cluster.bucket(bucket_name)

        # Get default collection 
        collection = bucket.default_collection()

        return cluster, bucket, collection
    except Exception as e:
        print(f"An error occurred: {e}")
        raise e


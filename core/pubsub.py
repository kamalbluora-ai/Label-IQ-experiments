import os
import json
from google.cloud import pubsub_v1

GCP_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("DOCAI_PROJECT", "")

# Topics
FANOUT_TOPIC = os.environ.get("PUBSUB_FANOUT_TOPIC", "compliance-fan-out")
DONE_TOPIC = os.environ.get("PUBSUB_DONE_TOPIC", "compliance-group-done")

_publisher = None

def get_publisher():
    global _publisher
    if _publisher is None:
        _publisher = pubsub_v1.PublisherClient()
    return _publisher

def publish_fan_out(job_id: str, group: str, facts_path: str):
    """Publish a fan-out message to trigger an agent group."""
    publisher = get_publisher()
    topic_path = publisher.topic_path(GCP_PROJECT, FANOUT_TOPIC)

    message = {
        "job_id": job_id,
        "group": group,
        "facts_path": facts_path,
    }

    future = publisher.publish(
        topic_path,
        data=json.dumps(message).encode("utf-8"),
        job_id=job_id,
        group=group,
    )
    future.result()  # Block until published
    print(f"[PUB/SUB] Published fan-out: job={job_id}, group={group}")

def publish_group_done(job_id: str, group: str, agents_completed: list[str]):
    """Publish a group completion message for fan-in."""
    publisher = get_publisher()
    topic_path = publisher.topic_path(GCP_PROJECT, DONE_TOPIC)

    message = {
        "job_id": job_id,
        "group": group,
        "status": "done",
        "agents_completed": agents_completed,
    }

    future = publisher.publish(
        topic_path,
        data=json.dumps(message).encode("utf-8"),
        job_id=job_id,
        group=group,
    )
    future.result()
    print(f"[PUB/SUB] Published group-done: job={job_id}, group={group}")

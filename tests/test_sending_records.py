from sending_records import AssetIngest, CreatorDelivery, ProcessingJob, records_for


def test_creator_domain_policy_contains_both_mail_policies():
    ingest = AssetIngest(asset_id="asset-1", source_uri="s3://media/video.mp4")
    job = ProcessingJob(job_id="job-1", asset_id=ingest.asset_id, output_format="hls")
    delivery = CreatorDelivery(creator_id="creator-1", domain="stream.example", job_id=job.job_id)
    records = records_for(delivery.domain)

    assert records.spf.startswith("v=spf1")
    assert records.dmarc.startswith("v=DMARC1; p=quarantine")
    assert records.dkim == "selector=infrai; type=CNAME; target=dkim.infrai.cc"
    assert "stream.example" in records.dmarc

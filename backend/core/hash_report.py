import hashlib


def report_hash(
    report
):

    return hashlib.sha256(
        report.encode()
    ).hexdigest()

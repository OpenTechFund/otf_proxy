import datetime
from flask import request
from app import app
from app.models import Token, Domain, Mirror, Report
from . import db

## API
@app.route('/api/v1/help/', methods=['GET', 'POST'])
def help():
    """
    Return help info in JSON format
    """
    return {"commands" : ['report', 'help']}

@app.route('/api/v1/report/', methods=['POST'])
def report_domain():
    """
    Add report of domain to database
    """
    req_data = request.get_json()

    # is authentication token correct?

    try:
        auth_token = Token.query.filter_by(auth_token=req_data['auth_token']).first()
    except:
        return {"report" : "Database Error with token!"}
    if not auth_token:
        return {"report": "Unauthorized!"}

    now = datetime.datetime.now()

    # Have we seen this domain before?
    try:
        domain = Domain.query.filter_by(domain=req_data['domain']).first()
    except:
        return {"report" : "Database Error with domain query!"}

    if domain: # we've seen it before
        domain_id = domain.id
        # Have we seen the mirror before?
        try:
            mirror = Mirror.query.filter_by(mirror_url=req_data['mirror_url']).first()
        except:
            return {"report" : "Database Error with mirror query!"}
        if mirror:
            mirror_id = mirror.id
        else:
            mirror = False
    else: # Let's add it
        try:
            domain = Domain(domain=req_data['domain'])
            db.session.add(domain)
            db.session.commit()
        except:
            return {"report" : "Database Error with mirror addition!"}
        domain_id = domain.id
        mirror = False # No domain, no mirror
 
    # Add mirror
    if not mirror:
        mirror = Mirror(
            mirror_url=req_data['mirror_url'],
            domain_id=domain_id)
        try:
            db.session.add(mirror)
            db.session.commit()
        except:
            return {"report" : "Database Error with mirror addition!"}
        mirror_id = mirror.id

    # Make the report
    req_data['date_reported'] = now
    req_data['domain_id'] = domain_id
    req_data['mirror_id'] = mirror_id
    req_data.pop('domain')
    req_data.pop('mirror_url')
    try:
        report = Report(**req_data)
        db.session.add(report)
        db.session.commit()
    except:
        return {"report" : "Database Error with report!"}


    return {"report": "Successfully reported."}
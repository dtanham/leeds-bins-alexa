from __future__ import print_function
import pymysql
import requests
import json

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

from prod_env import *

conn = pymysql.connect(rds_host, user=name, passwd=password, db=db_name, connect_timeout=5)

# Fetch collection information from DB
def fetch_collection_information(prop_id):
    with conn.cursor() as cur:
        # Grab the connection
        cur.execute("select * from bin_collections where property_id=%s and collection_date > now() order by collection_date asc limit 1", prop_id)
        result = cur.fetchone()
        if result is not None:
            return result
        else:
            logger.info("Could not find information for: "+prop_id)
            return (-1,"","")

def fetch_location_from_address(address):
    with conn.cursor() as cur:
        cur.execute("select property_id, street from bin_locations where street=%s", (address.get('addressLine1','')))
        result = cur.fetchone()
    if result is not None:
        return result[0]
    # return "1032041"
    return "-1"

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_next_collection(event, session):
    session_attributes = {}
    speech_output = ""
    card_title = ""
    reprompt_text = ""
    should_end_session = True

    # Fetch the user's address
    consent_token = session['user']['permissions'].get('consentToken',"")

    if len(consent_token) < 1:
        card_title = "Leeds Bins - Permission required"
        speech_output = "Leeds Bins needs access to your address information in order to work properly. It may be that you need to allow this permission through the Alexa app."
        return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))

    device_id = event['context']['System']['device']['deviceId']
    r = requests.get("https://api.eu.amazonalexa.com/v1/devices/"+device_id+"/settings/address", headers={'Authorization':'Bearer '+consent_token})
    logger.info("Received a response: "+str(r.status_code))

    # Error if we don't receive a 200 response
    if r.status_code != 200:
        card_title = "Leeds Bins - Error"
        speech_output = "Leeds Bins needs access to your address information in order to work properly. It may be that you need to allow this permission through the Alexa app."
        return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))

    # Fetch the location ID from the user's adress
    logger.info("Street: "+r.json().get('addressLine1',''))
    location = fetch_location_from_address(r.json())
    logging.info("Fetched location: "+str(location))

    # Fetch the collection type and date for the location
    (property_id, collection_type, collection_date) = fetch_collection_information(location)

    if property_id < 0:
        card_title = "Leeds Bins"
        speech_output = "Leeds Bins needs access to your address information in order to work properly. It may be that you need to allow this permission through the Alexa app."
    else:
        # Build the response
        card_title = "Leeds Bins"
        speech_output += "The next collection in your area will be for " + collection_type + " bins, on " + str(collection_date)

    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = ""
    should_end_session = True
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Have a nice day!"
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


# --------------- Events ------------------

def on_session_started(event, session_started_request, session):
    """ Called when the session starts """

    logger.info("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])

    # Stash the device ID along with the user ID
    device_id = event['context']['System']['device']['deviceId']
    user_id = session['user']['userId']
    with conn.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS user_device (user_id varchar(255), device_id varchar(255))")
        cur.execute("DELETE FROM user_device WHERE device_id=%s", (device_id))
        cur.execute("INSERT INTO user_device (user_id, device_id) VALUES(%s, %s)", (device_id, user_id))
        conn.commit()


def on_launch(event, launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    logger.info("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    return get_generic_welcome_message()

def get_generic_welcome_message():
    return build_response({}, build_speechlet_response("Leeds Bins", "Welcome to Leeds Bins. Now you can find out which waste bins to take out when. Try asking: what's my next collection.", None, False))

def on_intent(event, intent_request, session):
    """ Called when the user specifies an intent for this skill """

    logger.info("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent == "NextBins":
        return get_next_collection(event, session)

    return get_generic_welcome_message()

def on_session_ended(event, session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    logger.info("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here?


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    logger.info("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """Check that this is being called by our skill"""
    logger.info("Calling app: "+str(event['session']['application']['applicationId']))
    if (event['session']['application']['applicationId'] !=
            "amzn1.ask.skill."+skill_id):
        logger.error("Invalid application ID")
        raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started(event, {'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event, event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event, event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event, event['request'], event['session'])

    # Otherwise deal with it gracefully
    logger.info("Unexpected request type:")
    logger.info(json.dumps(event))
    return build_response({}, build_speechlet_response("Leeds Bins", "Welcome to Leeds Bins. Now you can find out which waste bins to take out when. Try asking: what's my next collection.", None, False))

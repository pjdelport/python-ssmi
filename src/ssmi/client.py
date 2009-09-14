"""Python module for SSMI protocol to send/receive USSD and SMS."""

# Copyright 2009 Praekelt International, all rights reserved

# Imports

import time
from types import StringTypes

from twisted.internet import reactor, protocol


# Constants

LINKCHECK_PERIOD = 60.0

SSMI_HEADER = "SSMI"

SSMI_SEND_LOGIN = "1"
SSMI_SEND_SMS = "2"
SSMI_SEND_LINK_CHECK = "3"
SSMI_SEND_BINARY = "4"
SSMI_SEND_LOGOUT = "99"
SSMI_SEND_USSD = "110"
SSMI_SEND_WAP_PUSH = "112"

SSMI_RESPONSE_SEQ = "100"
SSMI_RESPONSE_ACK = "101"
SSMI_RESPONSE_NACK = "102"
SSMI_RESPONSE_TEXT_MESSAGE = "103"
SSMI_RESPONSE_DELIVERY_MESSAGE = "104"
SSMI_RESPONSE_FREEFORM_MESSAGE = "105"
SSMI_RESPONSE_BINARY_MESSAGE = "106"
SSMI_RESPONSE_PREMIUMRATED_MESSAGE = "107"
SSMI_RESPONSE_BINARY_PREMIUMRATED_MESSAGE = "108"
SSMI_RESPONSE_USSD = "110"
SSMI_RESPONSE_USSD_EXTENDED = "111"
SSMI_RESPONSE_EXTENDED_RETURN = "113"
SSMI_RESPONSE_EXTENDED_RETURN_BINARY = "116"
SSMI_RESPONSE_EXTENDED_PREMIUMRATED_MESSAGE = "117"
SSMI_RESPONSE_EXTENDED_BINARY_PREMIUMRATED_MESSAGE = "118"
SSMI_RESPONSE_REMOTE_LOGOUT = "199"

SSMI_USSD_TYPE_NEW = "1"
SSMI_USSD_TYPE_EXISTING = "2"
SSMI_USSD_TYPE_END = "3"
SSMI_USSD_TYPE_TIMEOUT = "4"
SSMI_USSD_TYPE_REDIRECT = "5"
SSMI_USSD_TYPE_NI = "6"

ack_reason = {
    "1": "Login OK",
    "2": "Link check response",
}

nack_reason = {
    "1": "Invalid username/password combination",
    "2": "Invalid/unknown message type",
    "3": "Could not parse message",
    "4": "Account suspended (non-payment or abuse)",
}

class SSMIClient(protocol.Protocol):
    """Client for SSMI"""

    def __init__(self, app_register_callback=None):
        """init SSMIClient.

        app_register_callback: lambda: callback for setup
          -- this callback should call back again to
             self.app_setup to set username, password,
             and other callbacks.
        """
        self._link_check_pending = 0
        if app_register_callback and type(
            app_register_callback)==type(lambda: 1):
            # register protocol with app
            app_register_callback(self)

    def app_setup(self, username, password, ussd_callback=None,
                  sms_callback=None, errback=None):
        """Set up application callbacks to handle receiving USSD or SMS.

        username: string -- username for SSMI service
        password: string -- password for SSMI service
        ussd_callback: lambda -- callback for data received
        sms_callback: lambda -- callback for SMS received
        errback: lambda -- callback for error handling
        """
        self._username = username
        self._password = password
        self._ussd_callback = ussd_callback
        self._sms_callback = sms_callback
        self._errback = errback  # WHUI
        print 'SSMIClient app_setup done'

    def connectionMade(self):
        """Handle connection establishment

        Log in
        """
        print 'SSMIClient logging in'
        self.transport.write("%s,%s,%s,%s\r" % (SSMI_HEADER,
                                                SSMI_SEND_LOGIN,
                                                self._username,
                                                self._password))
        self.updateCall = reactor.callLater(LINKCHECK_PERIOD, self.linkcheck)

    def linkcheck(self):
        print "SSMIClient linkcheck: ", time.time()
        self.updateCall = None
        if self._link_check_pending == 2:
            print 'SSMIClient Link check not acked 2 times, disconnecting'
            self.transport.loseConnection()
            return
        self.transport.write("%s,%s\r" % (SSMI_HEADER,
                                          SSMI_SEND_LINK_CHECK))
        self._link_check_pending = self._link_check_pending + 1
        self.updateCall = reactor.callLater(LINKCHECK_PERIOD, self.linkcheck)

    def dataReceived(self, data):
        print "SSMIClient RECV USSD:", data
        response = data.strip().split(',')
        # assumption: response[0] == SSMI_HEADER
        if not response[0] == SSMI_HEADER:
            print 'SSMIClient FAIL: No SSMI header. Aborting'
            reactor.stop()
        response_code = response[1]
        if response_code == SSMI_RESPONSE_ACK:
            reason = response[2]
            print 'SSMIClient ACK', ack_reason[reason]
            if reason == "2":
                # Link check acked
                self._link_check_pending = 0
        elif response_code == SSMI_RESPONSE_NACK:
            reason = response[2]
            print 'SSMIClient NACK', nack_reason[reason]
        elif response_code == SSMI_RESPONSE_USSD:
            msisdn, ussd_type, phase, message = response[2:6]
            if ussd_type == SSMI_USSD_TYPE_NEW:
                #print 'SSMIClient New session'
                pass
            elif ussd_type == SSMI_USSD_TYPE_EXISTING:
                #print 'SSMIClient Existing session'
                pass
            elif ussd_type == SSMI_USSD_TYPE_END:
                print 'SSMIClient End of session'
            elif ussd_type == SSMI_USSD_TYPE_TIMEOUT:
                print 'SSMIClient TIMEOUT'
            # Call a callback into the app with the message.
            if self._ussd_callback is not None:
                self._ussd_callback(msisdn, ussd_type, phase, message)
        #elif response_code == SSMI_RESPONSE_TEXT_MESSAGE
        #elif response_code == SSMI_RESPONSE_DELIVERY_MESSAGE
        #elif response_code == SSMI_RESPONSE_SEQ
        elif response_code == SSMI_RESPONSE_REMOTE_LOGOUT:
            ip = response[2]
            print 'SSMIClient REMOTE LOGOUT RECEIVED. Other IP address: %s' % ip
            self.transport.loseConnection()


# SSMI_RESPONSE_SEQ = "100"
# SSMI_RESPONSE_TEXT_MESSAGE = "103"
# SSMI_RESPONSE_DELIVERY_MESSAGE = "104"
# SSMI_RESPONSE_FREEFORM_MESSAGE = "105"
# SSMI_RESPONSE_BINARY_MESSAGE = "106"
# SSMI_RESPONSE_PREMIUMRATED_MESSAGE = "107"
# SSMI_RESPONSE_BINARY_PREMIUMRATED_MESSAGE = "108"
# SSMI_RESPONSE_USSD = "110"
# SSMI_RESPONSE_USSD_EXTENDED = "111"
# SSMI_RESPONSE_EXTENDED_RETURN = "113"
# SSMI_RESPONSE_EXTENDED_RETURN_BINARY = "116"
# SSMI_RESPONSE_EXTENDED_PREMIUMRATED_MESSAGE = "117"
# SSMI_RESPONSE_EXTENDED_BINARY_PREMIUMRATED_MESSAGE = "118"
# SSMI_RESPONSE_REMOTE_LOGOUT = "199"


    def connectionLost(self, reason):
        if self.updateCall:
            self.updateCall.cancel()
        self.updateCall = None
        print "SSMIClient Connection lost", reason

    def send_ussd(self, msisdn, message, ussd_type=SSMI_USSD_TYPE_EXISTING):
        """Send USSD.

        msisdn: string -- cellphone number of recipient
        message: string -- message content
        ussd_type: type of SSMI reply
        """
        if ussd_type not in [SSMI_USSD_TYPE_EXISTING, SSMI_USSD_TYPE_END,
                             SSMI_USSD_TYPE_REDIRECT, SSMI_USSD_TYPE_NI]:
            print 'SSMIClient send_ussd bad ussd_type: %r' % ussd_type
            return
        if not type(message) in StringTypes:
            print 'SSMIClient send_ussd bad message type: %r' % message
            return
        self.transport.write(
            "%s,%s,%s,%s,%s\r" %
            (SSMI_HEADER, SSMI_SEND_USSD, msisdn,
             ussd_type, str(message)))

    def send_sms(self, msisdn, message, validity=0):
        """Send SMS.

        msisdn: string -- cellphone number of recipient
        message: string(160) -- message content
        validity: integer -- validity in minutes, default 0 for a week
        """
        self.transport.write(
            "%s,%s,%s,%s,%s\r" %
            (SSMI_HEADER, SSMI_SEND_SMS, str(validity), str(msisdn),
             str(message)))

    def send_wap_push(self, msisdn, subject, url):
        """Send a WAP Push.

        msisdn: string -- cellphone number of recipient
        subject: string -- subject displayed to subscriber
        url: string -- url to be sent to subscriber
        """
        self.transport.write(
            "%s,%s,%s,%s,%s\r" %
            (SSMI_HEADER, SSMI_SEND_WAP_PUSH, str(msisdn),
             str(subject), str(url)))


class SSMIFactory(protocol.ReconnectingClientFactory):
    def __init__(self, app_register_callback=None):
        """init SSMIFactory.

        app_register_callback: lambda: callback for setup
        """
        self._app_register_callback = app_register_callback

    def startConnecting(self, connector):
        print 'SSMIFactory Started to connect.'

    def buildProtocol(self, addr):
        print 'SSMIFactory Connected.'
        print 'SSMIFactory Resetting reconnection delay'
        self.resetDelay()
        return SSMIClient(app_register_callback=self._app_register_callback)

    def clientConnectionFailed(self, connector, reason):
        print "SSMIFactory Connection failed", reason
        protocol.ReconnectingClientFactory.clientConnectionFailed(
            self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        print "SSMIFactory Connection lost", reason
        protocol.ReconnectingClientFactory.clientConnectionLost(
            self, connector, reason)

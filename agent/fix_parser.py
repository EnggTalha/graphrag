"""
FIX Protocol parser and decoder.

Provides utilities for parsing and explaining FIX protocol messages.
Reference: Financial Information eXchange (FIX) - standard for securities transaction communication.
"""

# Standard FIX tag definitions
FIX_TAGS = {
    "8": ("BeginString", "FIX protocol version"),
    "9": ("BodyLength", "Number of bytes in the message body"),
    "10": ("CheckSum", "Three-byte simple checksum"),
    "34": ("MsgSeqNum", "Message sequence number"),
    "35": ("MsgType", "Identifies the type of message"),
    "49": ("SenderCompID", "Identifies the sending party"),
    "56": ("TargetCompID", "Identifies the target/receiving party"),
    "52": ("SendingTime", "Time of message transmission (UTC)"),
    "108": ("HeartBtInt", "Heartbeat interval in seconds"),
    "98": ("EncryptMethod", "Method of encryption (0=None, 1=PKCS, etc)"),
    "95": ("SecDataLen", "Length of SecData field"),
    "96": ("SecData", "Binary security data"),
    "11": ("ClOrdID", "Unique order ID assigned by client"),
    "12": ("Commission", "Commission amount"),
    "13": ("CommType", "Commission type (1=Percent, 2=Absolute, etc)"),
    "15": ("Currency", "Trade currency (e.g., USD, EUR)"),
    "16": ("IssueDate", "Security issue date"),
    "17": ("ExecID", "Unique execution ID"),
    "18": ("ExecRefID", "Reference to previous execution"),
    "20": ("ExecTransType", "Execution transaction type (0=New, 1=Cancel, 2=Correct)"),
    "21": ("HandlInst", "Order handling instruction (1=Automate, 2=Manual)"),
    "22": ("SecurityIDSource", "Source of SecurityID (e.g., CUSIP, ISIN)"),
    "25": ("IOIid", "IOI (Indication of Interest) ID"),
    "29": ("DeliverToSubID", "Delivery party sub-ID"),
    "30": ("DeliverToLocationID", "Delivery party location ID"),
    "31": ("ExecBroker", "Broker providing execution"),
    "32": ("ExecCommission", "Commission for execution"),
    "37": ("OrderID", "Unique order ID assigned by broker"),
    "38": ("OrderQty", "Order quantity in lots/units"),
    "39": ("OrdStatus", "Order status (0=New, 1=Partial, 2=Filled, 3=Done, 4=Canceled, 5=Replaced, 6=Pending, 8=Rejected)"),
    "40": ("OrdType", "Order type (1=Market, 2=Limit, 3=Stop, 4=StopLimit, etc)"),
    "41": ("OrigClOrdID", "Original client order ID"),
    "44": ("Price", "Price per unit"),
    "47": ("PartyIDSource", "Party ID source (D=DUNS, 1=CUSIP, etc)"),
    "48": ("SecurityID", "Security identifier (CUSIP, ISIN, etc)"),
    "54": ("Side", "Side of transaction (1=Buy, 2=Sell, 3=BuySell, 4=SellBuy)"),
    "55": ("Symbol", "Security symbol or code"),
    "58": ("Text", "Free-form text message"),
    "59": ("TimeInForce", "Time in force (0=Day, 1=GTC, 2=OPG, 3=Immediate, 4=Fill/Kill, 5=FOK, 6=GTX, 7=GTD)"),
    "60": ("TransactTime", "Transaction timestamp"),
    "61": ("Urgency", "Message urgency (0=Normal, 1=Flash, 2=Background)"),
    "63": ("SettlmntType", "Settlement type (0=Regular, 1=Cash, 2=Next Day, T+2, T+3, etc)"),
    "64": ("FutSettDate", "Future settlement date"),
    "65": ("SymbolSfx", "Symbol suffix"),
    "100": ("ExDestination", "Execution destination (exchange code)"),
    "107": ("SecurityDesc", "Security description"),
    "109": ("ClientID", "Client ID"),
    "110": ("TradingSessionID", "Trading session ID"),
    "119": ("PutOrCall", "Put or call option (0=Put, 1=Call)"),
    "120": ("StrikePrice", "Option strike price"),
    "167": ("SecurityType", "Security type (CS=Common Stock, OPT=Option, FUT=Future, etc)"),
    "200": ("MaturityMonthYear", "Maturity month and year"),
    "207": ("SecurityExchange", "Security exchange (NYSE, NASDAQ, etc)"),
    "208": ("RatioQty", "Ratio quantity"),
    "209": ("SecurityAltID", "Alternate security ID"),
    "210": ("SecurityAltIDSource", "Source of alternate security ID"),
    "211": ("UnderlyingSymbol", "Underlying security symbol"),
    "214": ("XmlDataLen", "XML data length"),
    "215": ("XmlData", "XML data field"),
    "231": ("MaturityDate", "Maturity date"),
    "262": ("MDReqID", "Market data request ID"),
    "263": ("SubscriptionRequestType", "Subscribe/Unsubscribe (0=Subscribe, 1=Unsubscribe)"),
    "264": ("MarketDepth", "Market depth (number of price levels)"),
}

# Message type codes
FIX_MSG_TYPES = {
    "0": ("Heartbeat", "Test message to confirm connection"),
    "1": ("TestRequest", "Test request to verify connectivity"),
    "2": ("ResendRequest", "Request to resend lost messages"),
    "3": ("ResendReply", "Response to resend request"),
    "4": ("SequenceReset", "Reset message sequence"),
    "5": ("Logout", "Terminate connection gracefully"),
    "8": ("ExecutionReport", "Report execution of order"),
    "9": ("OrderCancelReject", "Rejection of order cancellation"),
    "A": ("Logon", "Initiate connection and authentication"),
    "B": ("News", "News message"),
    "C": ("Email", "Email message"),
    "D": ("NewOrderSingle", "Submit new order"),
    "E": ("NewOrderList", "Submit multiple orders"),
    "F": ("OrderCancelRequest", "Request to cancel order"),
    "G": ("OrderCancelReplaceRequest", "Request to modify order"),
    "H": ("OrderStatusRequest", "Query order status"),
    "J": ("AllocationInstruction", "Allocation instruction"),
    "K": ("ListCancelRequest", "Request to cancel order list"),
    "L": ("ListExecute", "Execute order list"),
    "M": ("ListStatusRequest", "Request list status"),
    "N": ("ListStatus", "List status report"),
    "P": ("AllocationInstructionAck", "Allocation acknowledgement"),
    "Q": ("DontKnowTrade", "DK (Don't Know) trade"),
    "R": ("QuoteRequest", "Request price quote"),
    "S": ("Quote", "Price quote"),
    "T": ("SettlementInstructions", "Settlement instructions"),
    "V": ("MarketDataRequest", "Request market data"),
    "W": ("MarketDataSnapshotFullRefresh", "Market data snapshot"),
    "X": ("MarketDataIncrementalRefresh", "Incremental market data"),
    "Y": ("MarketDataRequestReject", "Market data request rejection"),
    "Z": ("QuoteCancel", "Cancel quote"),
    "AA": ("QuoteStatusRequest", "Request quote status"),
    "AB": ("MassQuoteAck", "Acknowledge mass quote"),
    "AC": ("SecurityDefinition", "Security definition"),
    "AD": ("SecurityDefinitionUpdateReport", "Security definition update"),
    "AE": ("LogoutRequest", "Logout request"),
    "AF": ("IOIMessage", "IOI (Indication of Interest) message"),
    "AG": ("Advertisement", "Advertisement"),
    "AH": ("SettlementInstructionResponse", "Settlement instruction response"),
    "AI": ("MassListStatusRequest", "Mass list status request"),
    "AJ": ("MassListStatusResponse", "Mass list status response"),
}

# Side codes
SIDE_CODES = {
    "1": "Buy",
    "2": "Sell",
    "3": "Buy Sell",
    "4": "Sell Buy",
    "5": "Correction Buy",
    "6": "Correction Sell",
    "7": "Correction Buy Sell",
    "8": "Correction Sell Buy",
}

# Order Status codes
ORDER_STATUS = {
    "0": "New",
    "1": "Partially Filled",
    "2": "Filled",
    "3": "Done for Day",
    "4": "Cancelled",
    "5": "Replaced",
    "6": "Pending Cancel",
    "7": "Stopped",
    "8": "Rejected",
    "9": "Suspended",
    "A": "Pending New",
    "B": "Calculated",
    "C": "Expired",
    "D": "Accepted for Bidding",
    "E": "Pending Replace",
}

# Order Type codes
ORDER_TYPE = {
    "1": "Market",
    "2": "Limit",
    "3": "Stop",
    "4": "Stop Limit",
    "5": "Trailing Stop",
    "6": "Trailing Stop Limit",
    "7": "Pegged",
}

# Time in Force codes
TIME_IN_FORCE = {
    "0": "Day",
    "1": "Good Till Cancel (GTC)",
    "2": "At Opening (OPG)",
    "3": "Immediate or Cancel (IOC)",
    "4": "Fill or Kill (FOK)",
    "5": "Good Till Crossing (GTX)",
    "6": "Good Till Date (GTD)",
    "7": "At Close (COL)",
}


def parse_fix_message(message_str: str) -> dict:
    """
    Parse a FIX message string and return structured data.
    
    Args:
        message_str: FIX message string (e.g., "8=FIX.4.4^9=100^35=D^...")
        
    Returns:
        Dictionary with parsed message data
    """
    # Detect delimiter - FIX uses SOH (ASCII 1) but often shown as ^ in plain text
    if "^" in message_str and chr(1) not in message_str:
        delimiter = "^"
    else:
        delimiter = chr(1)
    
    fields = {}
    pairs = message_str.split(delimiter)
    
    for pair in pairs:
        if "=" in pair:
            tag, value = pair.split("=", 1)
            fields[tag.strip()] = value.strip()
    
    return fields


def explain_fix_message(message_str: str) -> str:
    """
    Parse a FIX message and return a detailed human-readable explanation.
    
    Args:
        message_str: FIX message string
        
    Returns:
        Formatted explanation of the message
    """
    fields = parse_fix_message(message_str)
    
    if not fields:
        return "Invalid FIX message format. Expected format: 8=FIX.4.x^9=length^35=msgtype^..."
    
    # Extract key fields
    fix_version = fields.get("8", "Unknown")
    msg_type_code = fields.get("35", "Unknown")
    sender = fields.get("49", "Unknown")
    target = fields.get("56", "Unknown")
    
    # Lookup message type
    msg_type_name, msg_type_desc = FIX_MSG_TYPES.get(msg_type_code, ("Unknown", "Unknown message type"))
    
    # Build explanation
    explanation = f"""## FIX Protocol Message Decoder

### Message Overview
**Type**: {msg_type_name} (Code: {msg_type_code})
**Description**: {msg_type_desc}

**Protocol Version**: {fix_version}
**Sender**: {sender}
**Target/Recipient**: {target}

"""
    
    # Add field details
    explanation += "### Message Fields\n\n"
    explanation += "| Tag | Field Name | Value | Description |\n"
    explanation += "|-----|-----------|-------|-------------|\n"
    
    for tag in sorted(fields.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        value = fields[tag]
        tag_name, tag_desc = FIX_TAGS.get(tag, (f"Tag {tag}", "Custom/Unknown field"))
        
        # Decode special fields
        decoded_value = value
        if tag == "39" and value in ORDER_STATUS:  # OrdStatus
            decoded_value = f"{value} ({ORDER_STATUS[value]})"
        elif tag == "40" and value in ORDER_TYPE:  # OrdType
            decoded_value = f"{value} ({ORDER_TYPE[value]})"
        elif tag == "54" and value in SIDE_CODES:  # Side
            decoded_value = f"{value} ({SIDE_CODES[value]})"
        elif tag == "59" and value in TIME_IN_FORCE:  # TimeInForce
            decoded_value = f"{value} ({TIME_IN_FORCE[value]})"
        
        explanation += f"| {tag} | {tag_name} | {decoded_value} | {tag_desc} |\n"
    
    # Add plain English summary
    explanation += "\n### Plain English Summary\n\n"
    
    if msg_type_code == "D":  # NewOrderSingle
        side = SIDE_CODES.get(fields.get("54"), "Unknown")
        symbol = fields.get("55", "Unknown")
        qty = fields.get("38", "Unknown")
        price = fields.get("44", "N/A")
        ord_type = ORDER_TYPE.get(fields.get("40"), "Unknown")
        tif = TIME_IN_FORCE.get(fields.get("59", "0"), "Day")
        explanation += f"This is a **New Order** request to {side.lower()} {qty} shares of {symbol} at ${price} ({ord_type}) with time in force: {tif}."
    
    elif msg_type_code == "8":  # ExecutionReport
        status = ORDER_STATUS.get(fields.get("39"), "Unknown")
        symbol = fields.get("55", "Unknown")
        qty = fields.get("38", "Unknown")
        filled_qty = fields.get("14", "0")
        explanation += f"This is an **Execution Report** for {symbol}. Order status: {status}. Quantity: {qty} shares, Filled: {filled_qty} shares."
    
    elif msg_type_code == "F":  # OrderCancelRequest
        order_id = fields.get("37", "Unknown")
        symbol = fields.get("55", "Unknown")
        explanation += f"This is a **Cancel Request** for order {order_id} ({symbol})."
    
    elif msg_type_code == "A":  # Logon
        heartbeat = fields.get("108", "30")
        explanation += f"This is a **Logon** message to establish a connection. Heartbeat interval: {heartbeat} seconds."
    
    elif msg_type_code == "5":  # Logout
        explanation += f"This is a **Logout** message to terminate the connection."
    
    elif msg_type_code == "0":  # Heartbeat
        explanation += f"This is a **Heartbeat** message to confirm the connection is alive."
    
    else:
        explanation += f"This is a {msg_type_name} message."
    
    explanation += "\n\n### Common FIX Codes Reference\n\n"
    explanation += "**Order Status (39)**:\n"
    for code, status in sorted(ORDER_STATUS.items()):
        explanation += f"- {code}: {status}\n"
    
    return explanation


def is_fix_message(text: str) -> bool:
    """
    Check if the text contains a FIX message.
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears to be a FIX message
    """
    # Check for FIX message patterns
    return (
        ("8=FIX" in text and "^35=" in text) or  # Standard FIX format
        ("8=FIX" in text and chr(1) + "35=" in text)  # FIX with SOH delimiter
    )

#!/usr/bin/env python

# Ad slot auction simulator
# CS186, Harvard University

# All math is done using integers to avoid dealing with floating point:
#  - bids and budgets are specified in integer cents
#  - clicks / slot is rounded to the nearest click

from optparse import OptionParser
import copy
import itertools
import logging
import math
import pprint
import random
import sys

from gsp import GSP
from vcg import VCG
from history import History
from stats import Stats

#from bbagent import BBAgent
#from truthfulagent import TruthfulAgent

from util import argmax_index, shuffled, mean, stddev

# Infinite stream of zeros
zeros = itertools.repeat(0)

def iround(x):
    """Round x and return an int"""
    return int(round(x))

def agent_slot(occupants, a_id, t):
    """Return the slot agent with id a_id occupied in round t,
    or -1 if a_id wasn't present in round t"""
    agents = occupants[t]
    if a_id in agents:
        return agents.index(a_id)
    else:
        return -1


def sim(config):
    # TODO: Create agents here
    agents = init_agents(config)
    # Uncomment to print agents.
    #for a in agents:
    #    logging.info(a)

    n = len(agents)
    by_id = dict((a.id, a) for a in agents)
    agent_ids = [a.id for a in agents]

    if (config.mechanism.lower() == 'gsp' or
        config.mechanism.lower() == 'switch'):
        mechanism = GSP
    elif config.mechanism.lower() == 'vcg':
        mechanism = VCG
    else:
        raise ValueError("mechanism must be one of 'gsp', 'vcg', or 'switch'")

    reserve = config.reserve

    # Dictionaries : round # -> per_slot_list_of_whatever
    slot_occupants = {}
    slot_clicks = {}
    per_click_payments = {}
    slot_payments = {}
    values = {}
    bids = {}

    history = History(bids, slot_occupants, slot_clicks,
                      per_click_payments, slot_payments, n)

    def total_spent(agent_id, end):
        """
        Compute total amount spent by agent_id through (not including)
        round end.
        """
        s = 0
        for t in range(end):
            slot = agent_slot(slot_occupants, agent_id, t)
            if slot != -1:
                s += slot_payments[t][slot]
        return s

    def run_round(top_slot_clicks, t):
        """ top_slot_clicks is the expected number of clicks in the top slot
            k is the round number
        """
        if t == 0:
            bids[t] = [(a.id, a.initial_bid(reserve)) for a in agents]
        else:
            # Bids from agents with no money get reduced to zero
            have_money = lambda a: total_spent(a.id, t) < config.budget
            still_have_money = filter(have_money, agents)
            current_bids = []
            for a in agents:
                b = a.bid(t, history, reserve)
                if total_spent(a.id, t) < config.budget:
                    current_bids.append( (a.id, b))
                else:
                    # Out of money: make bid zero.
                    current_bids.append( (a.id, 0))
            bids[t] = current_bids

        ##   Ignore those below reserve price
        active_bidders = len(list(filter(lambda i_b: i_b[1] >= reserve, bids[t])))

        ##   1a.   Define no. of slots  (TO-DO: Check what the # of available slots should be)
        #num_slots = max(1, active_bidders-1)
        num_slots = max(1, n-1)

        ##   1b.  Calculate clicks/slot
        slot_clicks[t] = [iround(top_slot_clicks * pow(config.dropoff, i))
                          for i in range(num_slots)]

        ##  2. Run mechanism and allocate slots
        (slot_occupants[t], per_click_payments[t]) = (
            mechanism.compute(slot_clicks[t],
                              reserve, bids[t]))

        ##  3. Define payments
        slot_payments[t] = [x * y for x, y in zip(slot_clicks[t], per_click_payments[t])]

        ##  4.  Save utility (misnamed as values)
        values[t] = dict(zip(agent_ids, zeros))

        def agent_value(agent_id, clicks, payment):
            if agent_id:
                values[t][agent_id] = by_id[agent_id].value * clicks - payment
            return None
        
        list(map(agent_value, slot_occupants[t], slot_clicks[t], slot_payments[t]))
        
        ## Debugging. Set to True to see what's happening.
        log_console = False
        if log_console:
            logging.info("\t=== Round %d ===" % t)
            logging.info("\tnum_slots: %d" % num_slots)
            logging.info("\tbids: %s" % bids[t])
            logging.info("\tslot occupants: %s" % slot_occupants[t])
            logging.info("\tslot_clicks: %s" % slot_clicks[t])
            logging.info("\tper_click_payments: %s" % per_click_payments[t])
            logging.info("\tslot_payments: %s" % slot_payments[t])
            logging.info("\tUtility: %s" % values[t])
            logging.info("\ttotals spent: %s" % [total_spent(a.id, t+1) for a in agents])


    for t in range(0, config.num_rounds):
        # Over 48 rounds, go from 80 to 20 and back to 80.  Mean 50.
        # Makes sense when 48 rounds, to simulate a day
        top_slot_clicks = iround(80 - 60 * abs(t - (config.num_rounds / 2)) / (config.num_rounds / 2))
        run_round(top_slot_clicks, t)
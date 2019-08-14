#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of the Archivematica development tools.
#
# Copyright 2010-2016 Artefactual Systems Inc. <http://artefactual.com>
#
# Archivematica is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Archivematica is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Archivematica.    If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import gearman

try:
    import cPickle
except ModuleNotFoundError:
    import _pickle as cPickle

try:
    input = raw_input
except NameError:
    pass

import lxml.etree as etree
import traceback
import os
import time
import sys


class Settings:
    MCP_SERVER = ("localhost", 62004)


settings = Settings()


class MCPClient:
    def __init__(self, host=settings.MCP_SERVER[0], port=settings.MCP_SERVER[1]):
        self.server = "%s:%d" % (host, port)

    def list(self):
        gm_client = gearman.GearmanClient([self.server])
        completed_job_request = gm_client.submit_job(
            "getJobsAwaitingApproval", "", None
        )
        # self.check_request_status(completed_job_request)
        return cPickle.loads(completed_job_request.result)

    def execute(self, uuid, choice):
        gm_client = gearman.GearmanClient([self.server])
        data = {}
        data["jobUUID"] = uuid
        data["chain"] = choice
        data["uid"] = "1"
        completed_job_request = gm_client.submit_job(
            "approveJob", cPickle.dumps(data), None
        )
        # self.check_request_status(completed_job_request)
        return


mcpClient = MCPClient()


def getTagged(root, tag):  # bad, I use this elsewhere, should be imported
    ret = []
    for element in root:
        if element.tag == tag:
            ret.append(element)
            return ret  # only return the first encounter
    return ret


def updateJobsAwaitingApproval():
    return etree.XML(mcpClient.list())


def printJobsAwaitingApproval(jobsAwaitingApproval):
    for i, job in enumerate(jobsAwaitingApproval):
        print(i)
        print(etree.tostring(job, pretty_print=True, encoding="unicode"))


def approveJob(jobsAwaitingApproval, choice, choice2):
    try:
        index = int(choice)
        if index >= len(jobsAwaitingApproval):
            print("index out of range")
            return
        sipUUID = getTagged(
            getTagged(getTagged(jobsAwaitingApproval[index], "unit")[0], "unitXML")[0],
            "UUID",
        )[0].text
        uuid = getTagged(jobsAwaitingApproval[index], "UUID")[0].text
        try:
            chain = getTagged(
                getTagged(jobsAwaitingApproval[index], "choices")[0][int(choice2)],
                "chainAvailable",
            )[0].text
        except IndexError:
            # Invalid choice, but no reason to fail catastrophically.
            return
        print("Approving: " + uuid, chain, sipUUID)
        mcpClient.execute(uuid, chain)
        del jobsAwaitingApproval[index]
    except ValueError:
        print("Value error")
        traceback.print_exc(file=sys.stdout)
        return


def main():
    """Primary entry point for this script"""
    os.system("clear")
    jobsAwaitingApproval = updateJobsAwaitingApproval()
    choice = "No-op"
    while choice != "q":
        while not (len(jobsAwaitingApproval)):
            print("Fetching...")
            time.sleep(2)
            jobsAwaitingApproval = updateJobsAwaitingApproval()
        printJobsAwaitingApproval(jobsAwaitingApproval)
        print("q to quit")
        print("u to update List")
        print("number to approve Job")
        choice = input("Please enter a value:")
        print("choice: " + choice)
        if choice == "u":
            jobsAwaitingApproval = updateJobsAwaitingApproval()
        else:
            if choice == "q":
                break
            choice2 = "No-op"
            while choice2 != "q":
                try:
                    printJobsAwaitingApproval(jobsAwaitingApproval[int(choice)][2])
                except IndexError:
                    # Invalid choice, simply go back to main loop.
                    break
                choice2 = input("Please enter a value:")
                print("choice2: " + choice2)
                approveJob(jobsAwaitingApproval, choice, choice2)
                choice2 = "q"
                # except:
                # print "invalid choice"
                # choice2 = "q"
        os.system("clear")


if __name__ == "__main__":
    main()

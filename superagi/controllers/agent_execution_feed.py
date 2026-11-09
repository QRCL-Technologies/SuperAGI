import asyncio
from datetime import datetime
import time
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from fastapi import HTTPException, Depends
from fastapi_jwt_auth import AuthJWT
from fastapi_sqlalchemy import db
from pydantic import BaseModel

from sqlalchemy.sql import asc

from superagi.agent.task_queue import TaskQueue
from superagi.helper.auth import check_auth, get_user_organisation
from superagi.helper.time_helper import get_time_difference
from superagi.models.agent_execution_permission import AgentExecutionPermission
from superagi.helper.feed_parser import parse_feed
from superagi.models.agent import Agent
from superagi.models.agent_execution import AgentExecution
from superagi.models.agent_execution_feed import AgentExecutionFeed
from superagi.lib.logger import logger
from superagi.agent.types.agent_workflow_step_action_types import AgentWorkflowStepAction
from superagi.models.workflows.agent_workflow_step import AgentWorkflowStep
from superagi.models.workflows.agent_workflow_step_wait import AgentWorkflowStepWait
from superagi.models.project import Project

import re
# from superagi.types.db import AgentExecutionFeedOut, AgentExecutionFeedIn

router = APIRouter()


class AgentExecutionFeedOut(BaseModel):
    id: int
    agent_execution_id: int
    agent_id: int
    feed: str
    role: str
    extra_info: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class AgentExecutionFeedIn(BaseModel):
    id: int
    agent_execution_id: int
    agent_id: int
    feed: str
    role: str
    extra_info: str

    class Config:
        orm_mode = True


def get_agent_execution_for_organisation(agent_execution_id: int, organisation):
    """Return the agent execution only if it belongs to a project of the given organisation, else raise 404."""
    agent_execution = None
    if agent_execution_id is not None and organisation is not None:
        agent_execution = (db.session.query(AgentExecution)
                           .join(Agent, Agent.id == AgentExecution.agent_id)
                           .join(Project, Project.id == Agent.project_id)
                           .filter(AgentExecution.id == agent_execution_id,
                                   Project.organisation_id == organisation.id)
                           .first())
    if agent_execution is None:
        raise HTTPException(status_code=404, detail="Agent Execution not found")
    return agent_execution


def get_agent_execution_feed_for_organisation(agent_execution_feed_id: int, organisation):
    """Return the agent execution feed only if its execution belongs to the given organisation, else raise 404."""
    db_agent_execution_feed = db.session.query(AgentExecutionFeed).filter(
        AgentExecutionFeed.id == agent_execution_feed_id).first()
    if not db_agent_execution_feed:
        raise HTTPException(status_code=404, detail="Agent Execution Feed not found")
    try:
        get_agent_execution_for_organisation(db_agent_execution_feed.agent_execution_id, organisation)
    except HTTPException:
        raise HTTPException(status_code=404, detail="Agent Execution Feed not found")
    return db_agent_execution_feed


# CRUD Operations
@router.post("/add", response_model=AgentExecutionFeedOut, status_code=201)
def create_agent_execution_feed(agent_execution_feed: AgentExecutionFeedIn,
                                organisation=Depends(get_user_organisation)):
    """
    Add a new agent execution feed.

    Args:
        agent_execution_feed (AgentExecutionFeed): The data for the agent execution feed.

    Returns:
        AgentExecutionFeed: The newly created agent execution feed.

    Raises:
        HTTPException (Status Code=404): If the associated agent execution is not found.
    """

    agent_execution = get_agent_execution_for_organisation(agent_execution_feed.agent_execution_id, organisation)

    db_agent_execution_feed = AgentExecutionFeed(agent_execution_id=agent_execution_feed.agent_execution_id,
                                                 feed=agent_execution_feed.feed, type=agent_execution_feed.type,
                                                 extra_info=agent_execution_feed.extra_info,
                                                 feed_group_id=agent_execution.current_feed_group_id)
    db.session.add(db_agent_execution_feed)
    db.session.commit()
    return db_agent_execution_feed


@router.get("/get/{agent_execution_feed_id}", response_model=AgentExecutionFeedOut)
def get_agent_execution_feed(agent_execution_feed_id: int,
                             organisation=Depends(get_user_organisation)):
    """
    Get an agent execution feed by agent_execution_feed_id.

    Args:
        agent_execution_feed_id (int): The ID of the agent execution feed.

    Returns:
        AgentExecutionFeed: The agent execution feed with the specified ID.

    Raises:
        HTTPException (Status Code=404): If the agent execution feed is not found.
    """

    return get_agent_execution_feed_for_organisation(agent_execution_feed_id, organisation)


@router.put("/update/{agent_execution_feed_id}", response_model=AgentExecutionFeedOut)
def update_agent_execution_feed(agent_execution_feed_id: int,
                                agent_execution_feed: AgentExecutionFeedIn,
                                organisation=Depends(get_user_organisation)):
    """
    Update a particular agent execution feed.

    Args:
        agent_execution_feed_id (int): The ID of the agent execution feed to update.
        agent_execution_feed (AgentExecutionFeed): The updated agent execution feed.

    Returns:
        AgentExecutionFeed: The updated agent execution feed.

    Raises:
        HTTPException (Status Code=404): If the agent execution feed or agent execution is not found.
    """

    db_agent_execution_feed = get_agent_execution_feed_for_organisation(agent_execution_feed_id, organisation)

    if agent_execution_feed.agent_execution_id:
        agent_execution = get_agent_execution_for_organisation(agent_execution_feed.agent_execution_id, organisation)
        db_agent_execution_feed.agent_execution_id = agent_execution.id

    if agent_execution_feed.type is not None:
        db_agent_execution_feed.type = agent_execution_feed.type
    if agent_execution_feed.feed is not None:
        db_agent_execution_feed.feed = agent_execution_feed.feed
    # if agent_execution_feed.extra_info is not None:
    #     db_agent_execution_feed.extra_info = agent_execution_feed.extra_info

    db.session.commit()
    return db_agent_execution_feed


@router.get("/get/execution/{agent_execution_id}")
def get_agent_execution_feed(agent_execution_id: int,
                                         organisation=Depends(get_user_organisation)):
    """
    Get agent execution feed with other execution details.

    Args:
        agent_execution_id (int): The ID of the agent execution.

    Returns:
        dict: The agent execution status and feeds.

    Raises:
        HTTPException (Status Code=404): If the agent run is not found in the user's organisation.
    """

    agent_execution = get_agent_execution_for_organisation(agent_execution_id, organisation)
    feeds = db.session.query(AgentExecutionFeed).filter_by(agent_execution_id=agent_execution_id).order_by(
        asc(AgentExecutionFeed.created_at)).all()
    # # parse json
    final_feeds = []
    error = ""
    for feed in feeds:
        if feed.error_message:
            if (agent_execution.last_shown_error_id is None) or (feed.id > agent_execution.last_shown_error_id):
                #new error occured
                error = feed.error_message
                agent_execution.last_shown_error_id = feed.id
                agent_execution.status = "ERROR_PAUSED"
                db.session.commit()
            if feed.id == agent_execution.last_shown_error_id and agent_execution.status == "ERROR_PAUSED":
                error = feed.error_message
        if feed.feed != "" and re.search(r"The current time and date is\s(\w{3}\s\w{3}\s\s?\d{1,2}\s\d{2}:\d{2}:\d{2}\s\d{4})",feed.feed) == None :
            final_feeds.append(parse_feed(feed))

    # get all permissions
    execution_permissions = db.session.query(AgentExecutionPermission).\
        filter_by(agent_execution_id=agent_execution_id). \
        order_by(asc(AgentExecutionPermission.created_at)).all()

    permissions = [
        {
                "id": permission.id,
                "created_at": permission.created_at,
                "response": permission.user_feedback,
                "status": permission.status,
                "tool_name": permission.tool_name,
                "question": permission.question,
                "user_feedback": permission.user_feedback,
                "time_difference": get_time_difference(permission.created_at, str(datetime.now()))
        } for permission in execution_permissions
    ]

    waiting_period = None

    if agent_execution.status == AgentWorkflowStepAction.WAIT_STEP.value:
        workflow_step = AgentWorkflowStep.find_by_id(db.session, agent_execution.current_agent_step_id)
        waiting_period = (AgentWorkflowStepWait.find_by_id(db.session, workflow_step.action_reference_id)).delay

    return {
        "status": agent_execution.status,
        "feeds": final_feeds,
        "permissions": permissions,
        "waiting_period": waiting_period,
        "errors": error
    }


@router.get("/get/tasks/{agent_execution_id}")
def get_execution_tasks(agent_execution_id: int,
                        organisation=Depends(get_user_organisation)):
    """
    Get agent execution tasks and completed tasks.

    Args:
        agent_execution_id (int): The ID of the agent execution.

    Returns:
        dict: The tasks and completed tasks for the agent execution.
    """
    get_agent_execution_for_organisation(agent_execution_id, organisation)
    task_queue = TaskQueue(str(agent_execution_id))
    tasks = []
    for task in task_queue.get_tasks():
        tasks.append({"name": task})
    completed_tasks = []
    for task in reversed(task_queue.get_completed_tasks()):
        completed_tasks.append({"name": task['task']})

    return {
        "tasks": tasks,
        "completed_tasks": completed_tasks
    }
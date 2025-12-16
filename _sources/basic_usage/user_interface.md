# Web Application

## Overview

In addition to the terminal-based interface, we also provide a web application interface for the terminal agent. This can provide a more intuitive and user-friendly experience for the users who are not used to the terminal interface. We provide three types of web application interfaces:
1. [gradio chat app](#gradio-chat-app)
2. [annotation tool](#annotation-tool)
3. [MongoDB viewer](#mongodb-viewer)

## Gradio Chat App

This is a gradio-based chat application that allows you to chat with the agent to perform a task. This will render the user, terminal and LLM messages in real-time. You can also edit the message

```bash
autopilot gradio --port 9000 --zmq-port 8999
```
Interactive chat interface for running autopilot tasks with real-time supervision.

## Annotation Tool
```bash
autopilot annotate --port 8003 --zmq-port 8004
```
Annotate benchmark tasks for creating training data.

## MongoDB Viewer

```bash
autopilot mongo_viewer --port 8005
```
Web interface for browsing and analyzing historical autopilot session data.

# Choose LLM Service

## Overview

For LLM API, we can use commercial API or self-deploymented API. (Ask Longxu for OpenAI/Claude/Gemini API)


### SAIL-Deployed Model

We have two persistent API for vanilla devstral model and human-data-trained devstral (recommended)
```
- name: devstral
    credentials:
      api_key: token-abc123
      base_url: https://vllm-doulx-devstral.sail.insea.io/v1
    parameters:
      model: ''
    priority: 0
  - name: devstral-sft-0904
    credentials:
      api_key: token-abc123
      base_url: https://vllm-wangtd-devstral-sft-0904.sail.insea.io/v1/
    parameters:
      model: ''
    priority: 0
```

If you want deploy your in SAIL Cluster, can try the following scripts

### Deploy Your OWN Model

```
### Build NodePort
kubectl expose pod oatagent-446e3e-job-t9xwh --port=8000 --target-port=8000 --name=vllm-nodeport --type=NodePort -n language

### Get Port
kubectl get svc vllm-nodeport -n language

### Get IP
kubectl get pod oatagent-446e3e-job-t9xwh -n language -o jsonpath='{.status.hostIP}' && echo

### Delete NodePort after Destroying Pod
kubectl delete svc vllm-nodeport -n language
```

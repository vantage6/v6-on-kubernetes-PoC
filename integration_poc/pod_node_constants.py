# Paths within the Node POD-container defined by convention - these must match the mountPaths on kubeconfs/node_pod_config.yaml

TASK_FILES_ROOT = '/app/tasks'
KUBE_CONFIG_FILE_PATH = '/app/.kube/config'  
V6_NODE_CONFIG_FILE = '/app/.v6node/configs/node_legacy_config.yaml'
V6_NODE_DATABASE_BASE_PATH = '/app/.databases/'
V6_NODE_FQDN = 'v6-node-pod.v6-pod-subdomain.v6-node' # Must be consistent with kubeconfs/node_pod_config.yaml
V6_NODE_PROXY_PORT = '5000' 
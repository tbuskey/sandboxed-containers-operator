# Hacking on the sandboxed-containers-operator

## Prerequisites
- Golang - 1.21.x
- Operator SDK version - 1.28.0
```shell
export ARCH=$(case $(uname -m) in x86_64) echo -n amd64 ;; aarch64) echo -n arm64 ;; *) echo -n $(uname -m) ;; esac)
export OS=$(uname | awk '{print tolower($0)}')
export OPERATOR_SDK_DL_URL=https://github.com/operator-framework/operator-sdk/releases/download/v1.28.0
curl -LO ${OPERATOR_SDK_DL_URL}/operator-sdk_${OS}_${ARCH}
install -m 755 operator-sdk_linux_amd64 ${SOME_DIR_IN_YOUR_PATH}/operator-sdk
```
- podman, podman-docker or docker
- Access to OpenShift cluster (4.12+)
- Container registry to storage images

### Get a token on registry.ci.openshift.org
Our builder and base images are curated images from OpenShift.
They are pulled from registry.ci.openshift.org, which require an authentication.
To get access to these images, you have to login and retrieve a token, following [these steps](https://docs.ci.openshift.org/docs/how-tos/use-registries-in-build-farm/#how-do-i-log-in-to-pull-images-that-require-authentication)

#### Using the token
If docker build does not automatically use the token in your authfile, it can be forced:
```shell
export IMAGE_AUTH='--authfile=~/.docker/config.json'
```
#### Using public images instead of token

If you cannot login to registry.ci.openshift.org, a temporary solution is to use
public images during build and test. At the time of writing, the following public images
does the trick.

```shell
export BUILDER_IMAGE=registry.ci.openshift.org/openshift/release:golang-1.21
export TARGET_IMAGE=registry.ci.openshift.org/origin/4.16:base
make docker-build
```

In summary:
- login to one of the clusters' console
- use the console's shortcut to get the commandline login command
- log in from the command line with the provided command
- use "oc registry login" to save the token locally
- set IMAGE_AUTH to force docker-build to use the token if needed
-- if you cannot login, use the public images

## Change catalog for private quay repo
### Set Environment Variables

Set your quay.io userid
```shell
export QUAY_USERID=<user>
export IMAGE_TAG_BASE=quay.io/${QUAY_USERID}/openshift-sandboxed-containers-operator
export IMG=quay.io/${QUAY_USERID}/openshift-sandboxed-containers-operator
```

### Overwrite catalog/index.yaml
If `IMAGE_TAG_BASE` was set, use `make catalog-init` to change `catalog/index.yaml` for your quay repo.  It will also overwrite `catalog.Dockerfile`

## Viewing available Make targets
```
make help
```
## Building Operator image
```
make docker-build
make docker-push
```
### Skipping tests in Make
Add SKIP_TESTS=1 when calling make.  ex:
```
make SKIP_TESTS=1 docker-build
```

## Building Operator bundle image

### If you are deploying in an OpenShift cluster
Modify SANDBOXED_CONTAINERS_EXTENSION in config/manager/manager.yaml before you __Make the bundle__
```shell
sed -ie 's/kata-containers/sandboxed-containers/' config/manager/manager.yaml
```

### Make the bundle
```
make bundle CHANNELS=candidate
make bundle-build
make bundle-push
```

## Building Catalog image
```
make catalog-build
make catalog-push
```

## Installing the Operator using OpenShift Web console

### Create Custom Operator Catalog

Create a new `CatalogSource` yaml. Replace `${QUAY_USERID}` with your quay.io user and
`${VERSION}` with the operator VERSION from the Makefile

```shell
cat > my_catalog.yaml <<EOF
apiVersion: operators.coreos.com/v1alpha1
kind: CatalogSource
metadata:
 name:  my-operator-catalog
 namespace: openshift-marketplace
spec:
 displayName: My Operator Catalog
 sourceType: grpc
 image:  quay.io/${QUAY_USERID}/openshift-sandboxed-containers-operator-catalog:v${VERSION}
 updateStrategy:
   registryPoll:
      interval: 5m

EOF
```
Deploy the catalog
```
oc apply -f my_catalog.yaml
```

The new operator should become available for installation from the OpenShift web console


## Installing the Operator using CLI

When deploying the Operator using CLI, cert-manager needs to be installed otherwise
webhook will not start. `cert-manager` is not required when deploying via the web console as OLM
takes care of webhook certificate management. You can read more on this [here]( https://olm.operatorframework.io/docs/advanced-tasks/adding-admission-and-conversion-webhooks/#deploying-an-operator-with-webhooks-using-olm)

### Install cert-manager
```
 oc apply -f https://github.com/jetstack/cert-manager/releases/download/v1.5.3/cert-manager.yaml
```

### Modify YAMLs
Uncomment all entries marked with `[CERTMANAGER]` in manifest files under `config/*`

### Deploy Operator
```
make install && make deploy
```




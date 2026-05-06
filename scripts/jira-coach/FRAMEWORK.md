# Jira Coach Framework: Why, Results, Prove, Design, Evidence

This document explains the five-pillar framework for complete Jira tickets.

## The Five Pillars

### 1. Why - Business Justification
**Purpose:** Explain why this ticket exists

**What to include:**
- Business justification and value
- Problem being solved
- Customer or user impact
- Strategic importance

**Examples:**
- "Customer requests for better authentication in confidential containers"
- "Security team requires mutual TLS for peer-to-peer communication"
- "Reduce pod startup time from 30s to <5s to improve user experience"

**Anti-examples:**
- ❌ "Implement feature X" (that's WHAT, not WHY)
- ❌ Just a Jira ticket ID reference
- ❌ "Because the product manager said so"

---

### 2. Results - What the Final Product Looks Like to the User
**Purpose:** Describe what the user observes when this is deployed

**What to include:**
- Objects/resources created (Pods, Deployments, ConfigMaps, Secrets, etc.)
- Log entries
  - which log?
- System output
- Status changes or state transitions
- Order of events
- Maxium time for each event and/or overall if > 1 minute
- UI elements or screen changes
- Anything concrete and observable
  - scriptable with a poll timeout preferred

**Examples:**
- "Creates a kata-remote RuntimeClass"
- "Adds peer-pod-controller Deployment to openshift-sandboxed-containers-operator namespace"
- "oc logs of the CAA pod(s) will show: 'Peer pod authentication successful' when pod starts"
- "Status page displays green checkmark next to 'Peer Pods'"
- "New 'Configure Peer Pods' button appears in the UI"
- "If pod creation takes > 5 minutes, it is a fail"

**Anti-examples:**
- ❌ "Users can deploy peer pods" (that's HOW to use it, belongs in Prove)
- ❌ "Implements authentication layer" (that's internal design)
- ❌ "The system is more secure" (too vague, not observable)

**Key distinction:** Results = WHAT you see and where, not HOW you get there

---

### 3. Prove - How End Users Deploy/Use the Feature
**Purpose:** Show how to use the feature to produce the Results

**What to include:**
- Cluster setup
  - specific instance?  GPU?  TDX/SNP? BM?
  - cluster changes from GA
- Deployment steps
  - differences from GA/docs
- Commands users run
- YAML/configuration users need to apply
- Other setup procedures
  - Especially differences from GA OSC on AWS/Azure/Aro/BM
  - coco, kata, peer-pods, BM?  Any it doesn't work on?
- "How-to" instructions
- Anything that is not in GA docs.
  - some things are not well known to everyone
- Links to internal docs that are known to be working

**Examples:**
```markdown
## Prove

- Cluster on Azure with instance X
- OSC installed and KataConfig is setup with peer-pods and not coco or kata
- Create a peer pod
    - wait for pod to be in running state
- Get actual instance
    - `curl -s -H "Metadata:true" "*" "http://169.254.169.254/metadata/instance/compute/vmSize?api-version=2023-07-01&format=text"`
- verify result:
   - actual instance == X
```

**Anti-examples:**
- ❌ "The controller watches for KataConfig changes" (internal behavior, belongs in Design)
- ❌ "Authentication uses mTLS certificates" (implementation detail, belongs in Design)
- ❌ Just acceptance criteria without showing HOW

**Key distinction:** Prove = HOW users use it (user-facing actions)

---

### 4. Design - Implementation Details
**Purpose:** Describe internal architecture and implementation (what users DON'T see)

**What to include:**
- Internal components and architecture
- How the system works under the hood
- Technical approach
- Data structures or algorithms
- Dependencies and libraries
- Code organization

**Examples:**
- "peer-pod-controller watches KataConfig resources and creates corresponding RuntimeClass objects"
- "Authentication uses mutual TLS with certificate rotation every 24h"
- "Cloud provider integration uses libvirt for local and AWS API for remote pods"
- "Internal state stored in ConfigMap `peer-pod-state`"

**Anti-examples:**
- ❌ "Users run oc apply" (user-facing, belongs in Prove)
- ❌ "Creates RuntimeClass objects" (observable outcome, belongs in Results)
- ❌ Repeating what's in Prove or Results

**Key distinction:** Design = Internal implementation users don't see

**Rule of thumb:**
- If a user needs to know it to use the feature → **Prove**
- If it's internal architecture/code → **Design**

---

### 5. Evidence - Code Location & Testing Proof
**Purpose:** Show where the code is and prove it was tested

**What to include:**
- PR/MR links to code changes
- Repository references
- Testing evidence:
  - CI pipeline results
  - Test output
  - QE verification notes
  - Screenshots of working feature
  - Manual test results
  - Code coverage reports

**Examples:**
- https://github.com/openshift/sandboxed-containers-operator/pull/2090
- https://github.com/openshift/kata-containers/pull/1234
- "CI pipeline passed: https://prow.ci.openshift.org/view/gs/..."
- "QE verified in comment https://issues.redhat.com/browse/OSC-1234?focusedCommentId=12345"
- "Test output shows all 15 test cases passing"
- Screenshot attached showing feature working

**Anti-examples:**
- ❌ Just saying "tested" without evidence
- ❌ Only PR links without testing proof
- ❌ "Will add PRs later" on a Done ticket

**Key distinction:** Evidence = Code location + Proof of testing (not just one or the other)

---

## Common Confusions & How to Avoid Them

### Results vs Prove

**Scenario:** User deploys a pod with kata-remote RuntimeClass

**❌ Wrong:**
- Results: "Users can deploy peer pods using oc create"
- Prove: "Creates kata-remote RuntimeClass"

**✅ Correct:**
- Results: "Creates kata-remote RuntimeClass, peer-pod Pods show Running status, logs show 'Peer pod started successfully'"
- Prove: "Run `oc create -f peerpod.yaml`, verify with `oc get pods`, check logs with `oc logs`"

**Remember:** Results = Observable outcome, Prove = Steps to get there

### Prove vs Design

**Scenario:** Feature uses mTLS for authentication

**❌ Wrong (all mixed together):**
- Prove: "The controller uses mTLS certificates rotated every 24h, users run oc apply"
- Design: "Users deploy using oc apply"

**✅ Correct:**
- Prove: "Deploy: `oc apply -f kataconfig-peerpods.yaml`, creates peer-pods with secure communication"
- Design: "peer-pod-controller implements mTLS authentication with 24h certificate rotation using cert-manager"

**Remember:** If users need to do it → Prove, If it happens internally → Design

### Evidence is More Than Just PRs

**❌ Incomplete:**
- Evidence: "https://github.com/openshift/sandboxed-containers-operator/pull/2090"

**✅ Complete:**
- Evidence:
  - Code: https://github.com/openshift/sandboxed-containers-operator/pull/2090
  - Testing: CI passed https://prow.ci.openshift.org/view/gs/...
  - QE verified: https://issues.redhat.com/browse/OSC-1234?focusedCommentId=12345
  - Manual test: Deployed to cluster, verified peer pods start successfully

**Remember:** Evidence = WHERE (code) + PROOF (testing)

---

## Quick Reference Table

| Pillar | Answers | User Perspective | Contains |
|--------|---------|------------------|----------|
| **Why** | Why does this exist? | Why should I care? | Business value, problem statement |
| **Results** | What does it look like? | What do I see? | Objects created, UI changes, logs |
| **Prove** | How do I use it? | What do I do? | Commands, deployment steps, YAML |
| **Design** | How does it work internally? | (I don't see this) | Architecture, algorithms, internals |
| **Evidence** | Where's the code? Is it tested? | Can I trust this works? | PRs, test results, CI output |

---

## Validation Scoring

Each aspect is scored 0-3:
- **0** = Missing entirely (CRITICAL if ticket is Done)
- **1** = Weak/minimal (brief mention, lacks detail)
- **2** = Adequate (present with reasonable detail)
- **3** = Strong (comprehensive, well-documented)

**Overall score** = (sum of aspect scores / 15) × 100

**Target:** 75%+ for complete ticket

**No aspect should be 0** (especially not on Done tickets)

---

## Tips for Writing Each Aspect

### Writing Results
Be concrete and specific:
- ✅ "Creates peer-pod-controller Deployment with 2 replicas"
- ❌ "Deploys the controller"

List observable outcomes:
- What objects exist that didn't before?
- What changed in the UI?
- What appears in logs?

### Writing Prove
Write it as instructions:
- Use imperative mood: "Apply the YAML", "Run this command"
- Include actual commands: `oc apply -f file.yaml`
- Show expected output
- Make it copy-paste-able

### Writing Design
Focus on internals:
- How components interact
- Why technical decisions were made
- What libraries/dependencies are used
- Data flow and state management

Don't repeat Prove or Results:
- If it's visible to users → Results
- If users need to do it → Prove
- Only internal details → Design

### Writing Evidence
Always include both:
1. **Code:** PR/MR links to implementation
2. **Testing:** Proof it was verified

For testing evidence:
- Link to CI results
- Paste test output
- Reference QE verification
- Include screenshots if helpful

---

## Example Complete Ticket

**Why:**
Customer requests for peer pods support in confidential containers. Enables running trusted workloads on remote infrastructure while maintaining local control plane. Critical for hybrid cloud deployments.

**Results:**
- Creates `kata-remote` RuntimeClass
- Creates `peer-pod-controller` Deployment in `openshift-sandboxed-containers-operator` namespace
- Peer pods show `Running` status in `oc get pods`
- Logs show: "Peer pod authentication successful"
- Status API shows: `"peerPodsEnabled": true`

**Prove:**
1. Create KataConfig with peer pods enabled:
   ```bash
   oc apply -f kataconfig-peerpods.yaml
   ```

2. Deploy a peer pod:
   ```yaml
   apiVersion: v1
   kind: Pod
   metadata:
     name: my-peerpod
   spec:
     runtimeClassName: kata-remote
     containers:
     - name: nginx
       image: nginx:latest
   ```

   ```bash
   oc create -f peerpod.yaml
   ```

3. Verify:
   ```bash
   oc get pods my-peerpod
   oc logs my-peerpod
   ```

**Design:**
- `peer-pod-controller` watches KataConfig resources
- When `peerPods.enabled: true`, creates kata-remote RuntimeClass
- Implements cloud provider interface for AWS/Azure/libvirt
- Uses mutual TLS for peer-pod authentication (cert rotation every 24h via cert-manager)
- State stored in ConfigMap `peer-pod-state` for restart recovery

**Evidence:**
- Code:
  - Controller: https://github.com/openshift/sandboxed-containers-operator/pull/2090
  - Cloud provider: https://github.com/openshift/kata-containers/pull/1234
- Testing:
  - CI: https://prow.ci.openshift.org/view/gs/origin-ci-test/pr-logs/pull/openshift_sandboxed-containers-operator/2090/...
  - QE verified: https://issues.redhat.com/browse/OSC-1234?focusedCommentId=98765
  - Manual test passed on AWS and libvirt

**Validation Output:**
```
PILLAR SCORES:
----------------------------------------
  Why          3/3  ✅
  Results      3/3  ✅
  Prove        3/3  ✅
  Design       2/3  ✓
  Evidence     3/3  ✅
----------------------------------------
  Overall      93%  (14/15 points)
```

**Score:** 93% (14/15) - Complete! ✅

---

## Common Questions

**Q: Can Prove and Results overlap?**
A: They should complement, not repeat. Results describes WHAT you see. Prove shows HOW to get there.

**Q: Where do acceptance criteria go?**
A: Split them:
- Observable outcomes → Results
- Steps to verify → Prove
- Internal requirements → Design

**Q: What if the ticket is just a bug fix?**
A: All aspects still apply:
- Why: Impact of the bug
- Results: What changes after fix
- Prove: How to reproduce fixed behavior
- Design: What code changed internally
- Evidence: Fix PR + verification

**Q: Do child stories need all five aspects?**
A: Yes, but level of detail varies:
- Feature/Epic: All five well-documented
- Story: Can be briefer, reference parent for Why
- Task: May have minimal Design if trivial

**Q: What if I don't know the Design yet?**
A: That's OK for new tickets! Start with Why and Results. Add Prove and Design as you plan. Add Evidence as you implement.

**Q: Must Evidence have both code AND testing?**
A: For Done tickets: YES. For In Progress: Code first, then testing. For New tickets: Not yet expected.

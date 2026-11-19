# tags

Where each tag of [../assets/tags.json](../assets/tags.json) and its items come from: a survey of how 35 documented systems name their parts and what they record of each.

## Domain

- **count**: how many of the 35 surveyed systems name that kind of node in the page read; an edge or area tag has no count, and its row names the systems or vocabularies that show it.
- **key item**: an item the `gaps` call asks for when an element lacks it.

## Tags

| kind | tag | systems | named by |
| --- | --- | --- | --- |
| node | `actor` | 11 | PostgreSQL, Kafka, TLS1.3, OAuth2, OIDC, dbt, Stripe, PagerDuty, GitHub PR review, Camunda BPMN, OWASP DFD |
| node | `service` | 14 | Kubernetes, PostgreSQL, Kafka, DNS, OAuth2, OIDC, Chromium, Airflow, Android, Anthropic agents, Bitcoin, Rails, microservices.io, OWASP DFD |
| node | `job` | 15 | GitHub Actions, Airflow, dbt, AWS Lambda, Linux CFS, Linux initrd boot, Game loop, Anthropic agents, MLflow, PagerDuty, RISC pipeline, Rails, n8n, microservices.io, Camunda BPMN |
| node | `endpoint` | 10 | Kubernetes, TCP, OAuth2, OIDC, Stripe, Anthropic agents, MLflow, PagerDuty, CAN bus, Rails |
| node | `dataStore` | 18 | Kubernetes, PostgreSQL, Git, DNS, Airflow, dbt, Elasticsearch, Linux initrd boot, Android arch, Event sourcing, Anthropic agents, MLflow, Cloudflare cache, Classic RISC pipeline, Bitcoin devguide, Rails, microservices.io, OWASP DFD |
| node | `queue` | 2 | Kafka, Linux CFS |
| node | `artifact` | 8 | Git, LLVM IR, Lambda, Linux boot, Event sourcing, MLflow, PagerDuty, Bitcoin |
| node | `trigger` | 8 | TCP, GitHub Actions, Airflow, Lambda, Stripe, Game loop, GitHub PR review, Camunda BPMN |
| node | `policy` | 8 | OAuth2, OIDC, Chromium, Lambda, Linux CFS, GitHub PR review, Cloudflare cache, Bitcoin |
| node | `router` | 6 | Anthropic agents, CAN bus, RISC pipeline, Rails, microservices.io, Camunda BPMN |
| node | `host` | 7 | Kubernetes, GitHub Actions, Airflow, Elasticsearch, Lambda, Linux CFS, CAN bus |
| node | `credential` | 4 | TLS1.3, OAuth2, OIDC, Stripe |
| node | `state` | 4 | TCP, Stripe, MLflow, GitHub PR review |
| edge | `call` | - | 17 (K8s, Postgres, TLS, OAuth2, OIDC, Chromium IPC, Airflow API, Stripe, Android, agents tool use, Rails, microservices, DNS, TCP, CAN, PR, BPMN) |
| edge | `publish` | - | 7 (Kafka, event sourcing, Stripe webhook, Lambda trigger, Airflow, GitHub events, BPMN message) |
| edge | `access` | - | 14 (Postgres, Git, Airflow metadata, dbt, DNS cache, Android repo, MLflow, event log, Rails, ES, Bitcoin, microservices, DFD, RISC) |
| edge | `sequence` | - | 9 (BPMN, GH steps, boot, game loop, pipeline, PagerDuty, n8n connection, saga, TCP handshake) |
| edge | `dependsOn` | - | 8 (Backstage dependsOn, dbt ref, Airflow DAG deps, GH job needs, Android layers, Lambda role, LLVM, Rails) |
| edge | `transition` | - | Harel's statecharts and SCXML: https://www.w3.org/TR/scxml/ |
| edge | `produces` | - | 8 (dbt, MLflow, Git commit parent, GH artifacts, Lambda package, boot initrd, Bitcoin, Event sourcing) |
| edge | `triggers` | - | 8 (as `trigger` node) |
| edge | `governs` | - | 8 (as `policy` node) |
| edge | `partOf` | - | 3 (Backstage partOf, UML composition, ArchiMate composition) |
| area | `module` | - | C4 system boundary, Backstage System/Domain, arc42 building blocks, n8n canvas group |
| area | `deployment` | - | Structurizr deploymentNode, arc42 deployment view, K8s cluster |
| area | `trustZone` | - | DFD trust boundary (OWASP, MS TMT), Chromium sandbox |
| area | `lane` | - | BPMN lane/pool, Backstage Group |
| area | `region` | - | Harel's statecharts, where one of a group of states is current: https://www.state-machine.com/doc/Harel87.pdf |
| area | `phase` | - | boot sequence, CI stages, RISC pipeline stages |

## Systems surveyed

| system | page read | what it records |
| --- | --- | --- |
| Kubernetes | https://kubernetes.io/docs/concepts/architecture/ | responsibilities, scaling (page truncated; kube-proxy not read) |
| PostgreSQL | https://www.postgresql.org/docs/current/tutorial-arch.html | roles, lifetime |
| Kafka | https://kafka.apache.org/intro | retention per topic, key, replication factor 3, event key/value/timestamp/headers |
| Git | https://git-scm.com/book/en/v2/Git-Internals-Git-Objects | tree entry mode/type/sha/name; commit tree/parent/author/message |
| TCP | https://www.rfc-editor.org/rfc/rfc9293.html | state list, header fields, MSL 2 min, TCB variables |
| TLS 1.3 | https://www.rfc-editor.org/rfc/rfc8446.html | message types, which messages carry which extension |
| DNS | https://www.rfc-editor.org/rfc/rfc1035.html | RR name/type/class/TTL/RDATA, SOA timers |
| OAuth 2.0 | https://www.rfc-editor.org/rfc/rfc6749.html | client id/type/redirect URIs; token scope/lifetime |
| OIDC Core | https://openid.net/specs/openid-connect-core-1_0.html | ID token claims iss/sub/aud/exp/iat |
| Chromium | https://www.chromium.org/developers/design-documents/multi-process-architecture/ | host objects, routing IDs, sandbox restrictions |
| GitHub Actions | https://docs.github.com/en/actions/get-started/understand-github-actions | behaviour only; artifact/secret not on page |
| Airflow | https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html | metadata DB holds task/DAG/variable state |
| dbt | https://docs.getdbt.com/docs/build/projects | one-line purpose each; field lists live elsewhere |
| Elasticsearch (thin) | https://www.elastic.co/guide/en/elasticsearch/reference/current/scalability.html | names only |
| LLVM | https://llvm.org/docs/LangRef.html | linkage, alignment, section, initializer |
| AWS Lambda | https://docs.aws.amazon.com/lambda/latest/dg/concepts-basics.html | package type (zip/image), policies |
| Stripe | https://docs.stripe.com/payments/payment-intents | amount, currency, status lifecycle, idempotency key, 22-char descriptor limit |
| Linux CFS | https://docs.kernel.org/scheduler/sched-design-CFS.html | vruntime, load, policy, nice, base_slice_ns |
| Linux initrd boot | https://docs.kernel.org/admin-guide/initrd.html | ordered boot steps |
| Android architecture | https://developer.android.com/topic/architecture | responsibility lists, single source of truth |
| Game loop | https://gameprogrammingpatterns.com/game-loop.html | FPS 60 = 16 ms, timestep, lag |
| Event sourcing | https://martinfowler.com/eaaDev/EventSourcing.html | event times (occurred, recorded) |
| Anthropic agents | https://www.anthropic.com/engineering/building-effective-agents | definitions only |
| MLflow | https://mlflow.org/docs/latest/ml/ | stages staging/production/archived, lineage |
| PagerDuty incident response | https://docs.pagerduty.com/ops-guides/incident-response-guide/different-roles | timeline, customer impact count, preventive actions |
| GitHub PR review | https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews | Approve/Request changes/Comment |
| Cloudflare cache (thin) | https://developers.cloudflare.com/cache/how-to/cache-rules/ | eligibility, duration, where |
| CAN bus (Wikipedia, secondary) | https://en.wikipedia.org/wiki/CAN_bus | 11/29-bit id, 0-8 data bytes, 120 ohm, 1 Mbit/s |
| Classic RISC pipeline (Wikipedia, secondary) | https://en.wikipedia.org/wiki/Classic_RISC_pipeline | state per stage |
| Bitcoin | https://developer.bitcoin.org/devguide/block_chain.html | 80-byte header, 100-block coinbase maturity |
| Rails | https://guides.rubyonrails.org/getting_started.html | route table, schema history |
| n8n | https://docs.n8n.io/workflows/components/ | ids only |
| microservices.io | https://microservices.io/patterns/microservices.html | ownership by team |
| Camunda BPMN primer | https://docs.camunda.io/docs/components/modeler/bpmn/bpmn-primer/ | token semantics |
| OWASP threat modelling | https://community.owasp.org/Threat_Modeling_Process | entry/exit points, assets, trust levels in separate ID tables |

## Vocabularies compared

| vocabulary | page read | fields |
| --- | --- | --- |
| C4 | https://c4model.com/abstractions | page lists no per-element fields |
| Backstage | https://backstage.io/docs/features/software-catalog/descriptor-format | Component: type, lifecycle, owner, system, providesApis, consumesApis, dependsOn; API: definition; Resource: owner, type, dependsOn |
| Structurizr DSL | https://docs.structurizr.com/dsl/language | name, description, technology, tags, url, properties, perspectives, instances |
| arc42 | https://arc42.org/overview | - |
| OpenTelemetry semconv | https://opentelemetry.io/docs/specs/semconv/ | - |
| MS Threat Modeling Tool | https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-getting-started | threat title, category, priority, status |
| AWS icons | https://aws.amazon.com/architecture/icons/ | category names only |

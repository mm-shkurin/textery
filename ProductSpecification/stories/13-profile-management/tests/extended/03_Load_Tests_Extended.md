> These are additional edge case tests. Implement after core tests pass.

# Profile management — Load Tests (Extended)

Same declared profile as the main file: **Throughput**.

---

## 1. Recovery Shapes

### 1.1 The profile read recovers its rate after the database blips
```gherkin
Given the configured throughput baseline
And accounts reading their profiles at the sustained page-view rate
When the database becomes briefly unavailable and then returns
Then the sustained rate is regained within the recovery window
And checked-out connections return to their idle baseline
```

*Threshold: the main file's sustained rate, regained within the recovery window. Catches a
pool that never returns to health after a blip — the failure mode that turns a ten-second
database hiccup into an outage lasting until a restart.*

### 1.2 A fleet reboot does not stampede the profile endpoint
```gherkin
Given accounts whose pages all start at once after an outage
When they all read their profiles
Then the request rate arriving at the endpoint stays under the ceiling
And the retries are spread rather than issued in lockstep
```

*Threshold: arrival rate under the ceiling during the restart window. Every open tab in the
fleet re-reads this endpoint at boot, so unjittered client retries are a self-inflicted
spike on the endpoint that just came back.*

---

## DSL Technical Reference

| DSL Statement | Technical Implementation |
|---------------|-------------------------|
| `the configured throughput baseline` | The project's load-test baseline per `ProductSpecification/ExpectedLoad.md` |
| `the sustained page-view rate` | Request rate over the measurement window, driven at the load runner |
| `checked-out connections` | Pool checkout gauge |
| `the retries are spread` | Client backoff with jitter on the shared profile fetch |

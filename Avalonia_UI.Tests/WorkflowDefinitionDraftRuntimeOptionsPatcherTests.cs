using System.Collections.Generic;
using System.Text.Json;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowDefinitionDraftRuntimeOptionsPatcherTests
{
    [TestMethod]
    public void ApplyWritesWorkflowRuntimeOptionsAndPreservesWorkflowShape()
    {
        var result = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "source",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "config": {"rows": 3}
                }
              ],
              "connections": [
                {"connection_id": "c1"}
              ],
              "metadata": {"owner": "tester"}
            }
            """,
            new RuntimeOptionsDraft
            {
                Workflow = new RuntimeOptionsWorkflowDraft
                {
                    Profile = "custom",
                    Telemetry = new RuntimeOptionsTelemetryDraft
                    {
                        LogLevel = "WARN",
                        EventLevel = "basic",
                        EventRateLimitPerSecond = 10,
                        ProgressEnabled = false,
                        ProgressIntervalSeconds = 5,
                    },
                    Diagnostics = new RuntimeOptionsDiagnosticsDraft
                    {
                        IncludeMetrics = false,
                        PayloadByteLimit = 65536,
                        TtlSeconds = 604800,
                        RedactColumns = ["password"],
                        MaskPolicy = "partial",
                    },
                },
            });

        Assert.IsTrue(result.Succeeded);
        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var root = updated.RootElement;
        Assert.AreEqual("1.0", root.GetProperty("schema_version").GetString());
        Assert.AreEqual("tester", root.GetProperty("metadata").GetProperty("owner").GetString());
        Assert.AreEqual("c1", root.GetProperty("connections")[0].GetProperty("connection_id").GetString());
        Assert.AreEqual(
            3,
            root.GetProperty("nodes")[0].GetProperty("config").GetProperty("rows").GetInt32());

        var runtimeOptions = root.GetProperty("runtime_options");
        Assert.AreEqual(
            "custom",
            runtimeOptions.GetProperty("workflow").GetProperty("profile").GetString());
        Assert.AreEqual(
            "WARN",
            runtimeOptions
                .GetProperty("workflow")
                .GetProperty("telemetry")
                .GetProperty("log_level")
                .GetString());
        Assert.IsFalse(
            runtimeOptions
                .GetProperty("workflow")
                .GetProperty("diagnostics")
                .GetProperty("include_metrics")
                .GetBoolean());
        Assert.AreEqual(
            "password",
            runtimeOptions
                .GetProperty("workflow")
                .GetProperty("diagnostics")
                .GetProperty("redact_columns")[0]
                .GetString());
        Assert.IsFalse(
            runtimeOptions.GetProperty("workflow").TryGetProperty(
                "strict_validation",
                out _));
        Assert.IsFalse(
            runtimeOptions
                .GetProperty("workflow")
                .GetProperty("diagnostics")
                .TryGetProperty("ttl_seconds", out _));
    }

    [TestMethod]
    public void ApplyWritesNodeOverrideAsDifferenceOnly()
    {
        var result = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            """{"schema_version":"1.0","nodes":[],"connections":[]}""",
            new RuntimeOptionsDraft
            {
                Workflow = new RuntimeOptionsWorkflowDraft
                {
                    Telemetry = new RuntimeOptionsTelemetryDraft
                    {
                        LogLevel = "INFO",
                        EventLevel = "progress",
                    },
                    Diagnostics = new RuntimeOptionsDiagnosticsDraft
                    {
                        IncludeMetrics = true,
                        RedactColumns = ["password"],
                    },
                },
                NodeOverrides =
                    new Dictionary<string, RuntimeOptionsNodeOverrideDraft>
                    {
                        ["node_1"] = new()
                        {
                            Telemetry = new RuntimeOptionsTelemetryOverrideDraft
                            {
                                LogLevel = "INFO",
                                EventLevel = "verbose",
                            },
                            Diagnostics = new RuntimeOptionsDiagnosticsOverrideDraft
                            {
                                IncludeMetrics = false,
                                RedactColumns = ["password"],
                            },
                        },
                    },
            });

        Assert.IsTrue(result.Succeeded);
        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var nodeOverride = updated.RootElement
            .GetProperty("runtime_options")
            .GetProperty("node_overrides")
            .GetProperty("node_1");
        var telemetry = nodeOverride.GetProperty("telemetry");
        Assert.IsFalse(telemetry.TryGetProperty("log_level", out _));
        Assert.AreEqual(
            "verbose",
            telemetry.GetProperty("event_level").GetString());

        var diagnostics = nodeOverride.GetProperty("diagnostics");
        Assert.IsFalse(diagnostics.GetProperty("include_metrics").GetBoolean());
        Assert.IsFalse(diagnostics.TryGetProperty("redact_columns", out _));
    }

    [TestMethod]
    public void ApplyDoesNotWriteRuntimeOptionsIntoNodeConfig()
    {
        var result = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            """
            {
              "nodes": [
                {
                  "node_instance_id": "node_1",
                  "config": {"field": "amount"}
                }
              ],
              "connections": []
            }
            """,
            new RuntimeOptionsDraft
            {
                NodeOverrides =
                    new Dictionary<string, RuntimeOptionsNodeOverrideDraft>
                    {
                        ["node_1"] = new()
                        {
                            Telemetry = new RuntimeOptionsTelemetryOverrideDraft
                            {
                                EventLevel = "verbose",
                            },
                        },
                    },
            });

        Assert.IsTrue(result.Succeeded);
        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var node = updated.RootElement.GetProperty("nodes")[0];
        Assert.AreEqual("amount", node.GetProperty("config").GetProperty("field").GetString());
        Assert.IsFalse(node.GetProperty("config").TryGetProperty("runtime_options", out _));
        Assert.IsFalse(node.GetProperty("config").TryGetProperty("__runtime", out _));
    }

    [TestMethod]
    public void ApplyPreservesCompatibilityOnlyFieldsWithoutUsingDraftValues()
    {
        var result = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            """
            {
              "nodes": [],
              "connections": [],
              "runtime_options": {
                "version": "1.0",
                "workflow": {
                  "profile": "custom",
                  "strict_validation": false,
                  "diagnostics": {
                    "ttl_seconds": 123
                  }
                },
                "node_overrides": {
                  "node_1": {
                    "strict_validation": false,
                    "diagnostics": {
                      "ttl_seconds": 456
                    }
                  }
                }
              }
            }
            """,
            new RuntimeOptionsDraft
            {
                Workflow = new RuntimeOptionsWorkflowDraft
                {
                    StrictValidation = true,
                    Diagnostics = new RuntimeOptionsDiagnosticsDraft
                    {
                        TtlSeconds = 999,
                    },
                },
                NodeOverrides = new Dictionary<string, RuntimeOptionsNodeOverrideDraft>
                {
                    ["node_1"] = new()
                    {
                        StrictValidation = true,
                        Diagnostics = new RuntimeOptionsDiagnosticsOverrideDraft
                        {
                            TtlSeconds = 999,
                        },
                    },
                },
            });

        Assert.IsTrue(result.Succeeded);
        using var updated = JsonDocument.Parse(
            result.UpdatedWorkflowDefinitionDraftJson);
        var runtimeOptions = updated.RootElement.GetProperty("runtime_options");
        var workflow = runtimeOptions.GetProperty("workflow");
        Assert.IsFalse(workflow.GetProperty("strict_validation").GetBoolean());
        Assert.AreEqual(
            123,
            workflow.GetProperty("diagnostics").GetProperty("ttl_seconds").GetInt32());
        var nodeOverride = runtimeOptions
            .GetProperty("node_overrides")
            .GetProperty("node_1");
        Assert.IsFalse(nodeOverride.GetProperty("strict_validation").GetBoolean());
        Assert.AreEqual(
            456,
            nodeOverride
                .GetProperty("diagnostics")
                .GetProperty("ttl_seconds")
                .GetInt32());
    }

    [TestMethod]
    public void ApplyRejectsInvalidWorkflowJson()
    {
        var result = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            "{",
            new RuntimeOptionsDraft());

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            WorkflowDefinitionDraftRuntimeOptionsPatchStatus.JsonInvalid,
            result.Status);
        Assert.AreEqual("WORKFLOW_DRAFT_JSON_INVALID", result.Warning);
    }

    [TestMethod]
    public void ApplyRejectsBlankNodeOverrideId()
    {
        var result = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            """{"nodes":[],"connections":[]}""",
            new RuntimeOptionsDraft
            {
                NodeOverrides =
                    new Dictionary<string, RuntimeOptionsNodeOverrideDraft>
                    {
                        [" "] = new(),
                    },
            });

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            WorkflowDefinitionDraftRuntimeOptionsPatchStatus.NodeInstanceIdRequired,
            result.Status);
        Assert.AreEqual("NODE_INSTANCE_ID_REQUIRED", result.Warning);
    }
}

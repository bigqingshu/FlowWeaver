using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class RuntimeOptionsDraftTests
{
    [TestMethod]
    public void ReadReturnsDefaultDraftWhenRuntimeOptionsMissing()
    {
        var result = RuntimeOptionsDraftReader.Read(
            """
            {
              "schema_version": "1.0",
              "nodes": [],
              "connections": []
            }
            """);

        Assert.IsTrue(result.Succeeded);
        Assert.AreEqual(RuntimeOptionsDraftReadStatus.Succeeded, result.Status);
        Assert.IsNull(result.Warning);
        Assert.AreEqual("1.0", result.Draft.Version);
        Assert.AreEqual("normal", result.Draft.Workflow.Profile);
        Assert.AreEqual("INFO", result.Draft.Workflow.Telemetry.LogLevel);
        Assert.AreEqual("progress", result.Draft.Workflow.Telemetry.EventLevel);
        Assert.IsTrue(result.Draft.Workflow.Telemetry.ProgressEnabled);
        Assert.IsTrue(result.Draft.Workflow.Diagnostics.IncludeMetrics);
        Assert.IsEmpty(result.Draft.NodeOverrides);
    }

    [TestMethod]
    public void ReadParsesWorkflowAndNodeOverrides()
    {
        var result = RuntimeOptionsDraftReader.Read(
            """
            {
              "runtime_options": {
                "version": "1.0",
                "workflow": {
                  "profile": "custom",
                  "strict_validation": false,
                  "telemetry": {
                    "log_level": "WARN",
                    "event_level": "basic",
                    "event_rate_limit_per_second": 10,
                    "progress_enabled": false,
                    "progress_interval_seconds": 5
                  },
                  "diagnostics": {
                    "capture_error_context": true,
                    "include_metrics": false,
                    "payload_byte_limit": 65536,
                    "ttl_seconds": 604800,
                    "redact_columns": ["password"],
                    "mask_policy": "partial"
                  }
                },
                "node_overrides": {
                  "node_1": {
                    "telemetry": {
                      "log_level": "DEBUG",
                      "event_level": "verbose"
                    },
                    "diagnostics": {
                      "include_metrics": true
                    }
                  }
                }
              }
            }
            """);

        Assert.IsTrue(result.Succeeded);
        Assert.AreEqual("custom", result.Draft.Workflow.Profile);
        Assert.IsFalse(result.Draft.Workflow.StrictValidation);
        Assert.AreEqual("WARN", result.Draft.Workflow.Telemetry.LogLevel);
        Assert.AreEqual(10, result.Draft.Workflow.Telemetry.EventRateLimitPerSecond);
        Assert.AreEqual("password", result.Draft.Workflow.Diagnostics.RedactColumns[0]);
        Assert.AreEqual("partial", result.Draft.Workflow.Diagnostics.MaskPolicy);

        var nodeOverride = result.Draft.NodeOverrides["node_1"];
        Assert.AreEqual("DEBUG", nodeOverride.Telemetry?.LogLevel);
        Assert.AreEqual("verbose", nodeOverride.Telemetry?.EventLevel);
        Assert.IsTrue(nodeOverride.Diagnostics?.IncludeMetrics);
    }

    [TestMethod]
    public void ReadRejectsInvalidWorkflowJson()
    {
        var result = RuntimeOptionsDraftReader.Read("{");

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(RuntimeOptionsDraftReadStatus.JsonInvalid, result.Status);
        Assert.AreEqual("WORKFLOW_DRAFT_JSON_INVALID", result.Warning);
    }

    [TestMethod]
    public void ReadRejectsNonObjectRuntimeOptions()
    {
        var result = RuntimeOptionsDraftReader.Read("""{"runtime_options": []}""");

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            RuntimeOptionsDraftReadStatus.RuntimeOptionsNotObject,
            result.Status);
        Assert.AreEqual("RUNTIME_OPTIONS_NOT_OBJECT", result.Warning);
    }
}

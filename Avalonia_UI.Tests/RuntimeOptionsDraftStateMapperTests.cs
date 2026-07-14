using System.Collections.Generic;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class RuntimeOptionsDraftStateMapperTests
{
    [TestMethod]
    public void ToWorkflowFieldStateFormatsWorkflowDraftForUiInputs()
    {
        var draft = new RuntimeOptionsWorkflowDraft
        {
            Profile = "custom",
            StrictValidation = false,
            Telemetry = new RuntimeOptionsTelemetryDraft
            {
                LogLevel = "WARN",
                EventLevel = "basic",
                EventRateLimitPerSecond = 10,
                ProgressEnabled = false,
                ProgressIntervalSeconds = 2.5,
            },
            Diagnostics = new RuntimeOptionsDiagnosticsDraft
            {
                CaptureErrorContext = false,
                IncludeMetrics = false,
                PayloadByteLimit = 65536,
                TtlSeconds = 604800,
                RedactColumns = ["password", "token"],
                MaskPolicy = "partial",
            },
        };

        var state = RuntimeOptionsDraftStateMapper.ToWorkflowFieldState(draft);

        Assert.AreEqual("custom", state.Profile);
        Assert.IsFalse(state.StrictValidation);
        Assert.AreEqual("WARN", state.LogLevel);
        Assert.AreEqual("basic", state.EventLevel);
        Assert.AreEqual("10", state.EventRateLimitPerSecond);
        Assert.IsFalse(state.ProgressEnabled);
        Assert.AreEqual("2.5", state.ProgressIntervalSeconds);
        Assert.IsFalse(state.CaptureErrorContext);
        Assert.IsFalse(state.IncludeMetrics);
        Assert.AreEqual("65536", state.PayloadByteLimit);
        Assert.AreEqual("604800", state.TtlSeconds);
        Assert.AreEqual("password, token", state.RedactColumns);
        Assert.AreEqual("partial", state.MaskPolicy);
    }

    [TestMethod]
    public void ToSelectedNodeFieldStateFallsBackToWorkflowValuesWhenNoOverrideExists()
    {
        var draft = new RuntimeOptionsDraft
        {
            Workflow = new RuntimeOptionsWorkflowDraft
            {
                Profile = "diagnostic",
                StrictValidation = false,
                Telemetry = new RuntimeOptionsTelemetryDraft
                {
                    LogLevel = "DEBUG",
                    EventLevel = "verbose",
                    EventRateLimitPerSecond = 3,
                    ProgressEnabled = false,
                    ProgressIntervalSeconds = 1.25,
                },
                Diagnostics = new RuntimeOptionsDiagnosticsDraft
                {
                    CaptureErrorContext = false,
                    IncludeMetrics = false,
                    PayloadByteLimit = 1024,
                    TtlSeconds = 30,
                    RedactColumns = ["secret"],
                    MaskPolicy = "full",
                },
            },
        };

        var state = RuntimeOptionsDraftStateMapper.ToSelectedNodeFieldState(
            draft,
            "node-1");

        Assert.AreEqual("diagnostic", state.Profile);
        Assert.IsFalse(state.StrictValidation ?? true);
        Assert.AreEqual("DEBUG", state.LogLevel);
        Assert.AreEqual("verbose", state.EventLevel);
        Assert.AreEqual("3", state.EventRateLimitPerSecond);
        Assert.IsFalse(state.ProgressEnabled ?? true);
        Assert.AreEqual("1.25", state.ProgressIntervalSeconds);
        Assert.IsFalse(state.CaptureErrorContext ?? true);
        Assert.IsFalse(state.IncludeMetrics ?? true);
        Assert.AreEqual("1024", state.PayloadByteLimit);
        Assert.AreEqual("30", state.TtlSeconds);
        Assert.AreEqual("secret", state.RedactColumns);
        Assert.AreEqual("full", state.MaskPolicy);
    }

    [TestMethod]
    public void ToSelectedNodeFieldStateOverlaysNodeOverrideValues()
    {
        var draft = new RuntimeOptionsDraft
        {
            Workflow = new RuntimeOptionsWorkflowDraft
            {
                Profile = "normal",
                Telemetry = new RuntimeOptionsTelemetryDraft
                {
                    LogLevel = "INFO",
                    EventLevel = "progress",
                    EventRateLimitPerSecond = 1,
                    ProgressEnabled = true,
                    ProgressIntervalSeconds = 0.5,
                },
                Diagnostics = new RuntimeOptionsDiagnosticsDraft
                {
                    CaptureErrorContext = true,
                    IncludeMetrics = true,
                    PayloadByteLimit = 2048,
                    TtlSeconds = 60,
                    RedactColumns = ["workflow_secret"],
                    MaskPolicy = "none",
                },
            },
            NodeOverrides = new Dictionary<string, RuntimeOptionsNodeOverrideDraft>
            {
                ["node-1"] = new()
                {
                    Profile = "background_fast",
                    Telemetry = new RuntimeOptionsTelemetryOverrideDraft
                    {
                        LogLevel = "ERROR",
                        ProgressEnabled = false,
                    },
                    Diagnostics = new RuntimeOptionsDiagnosticsOverrideDraft
                    {
                        PayloadByteLimit = 4096,
                        RedactColumns = ["node_secret"],
                    },
                },
            },
        };

        var state = RuntimeOptionsDraftStateMapper.ToSelectedNodeFieldState(
            draft,
            "node-1");

        Assert.AreEqual("background_fast", state.Profile);
        Assert.IsTrue(state.StrictValidation ?? false);
        Assert.AreEqual("ERROR", state.LogLevel);
        Assert.AreEqual("progress", state.EventLevel);
        Assert.AreEqual("1", state.EventRateLimitPerSecond);
        Assert.IsFalse(state.ProgressEnabled ?? true);
        Assert.AreEqual("0.5", state.ProgressIntervalSeconds);
        Assert.IsTrue(state.CaptureErrorContext ?? false);
        Assert.IsTrue(state.IncludeMetrics ?? false);
        Assert.AreEqual("4096", state.PayloadByteLimit);
        Assert.AreEqual("60", state.TtlSeconds);
        Assert.AreEqual("node_secret", state.RedactColumns);
        Assert.AreEqual("none", state.MaskPolicy);
    }

    [TestMethod]
    public void ParseRedactColumnsSplitsTrimsAndDeduplicatesValues()
    {
        var columns = RuntimeOptionsDraftStateMapper.ParseRedactColumns(
            " password, token; password\r\napi_key ");

        CollectionAssert.AreEqual(
            new[] { "password", "token", "api_key" },
            new List<string>(columns));
    }

    [TestMethod]
    public void ParseRedactColumnsTreatsNullAsEmptyInput()
    {
        var columns = RuntimeOptionsDraftStateMapper.ParseRedactColumns(null);

        Assert.IsEmpty(columns);
    }
}

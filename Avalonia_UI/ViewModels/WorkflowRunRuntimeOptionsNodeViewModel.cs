using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public sealed class WorkflowRunRuntimeOptionsNodeViewModel : ViewModelBase
{
    public WorkflowRunRuntimeOptionsNodeViewModel(
        string nodeInstanceId,
        ResolvedRuntimeFeedbackPolicyDto effectivePolicy,
        RuntimeFeedbackPolicyOverrideDraft draft,
        IReadOnlyList<ActiveNodeTaskRuntimeOptionsVersionDto> activeTasks,
        int requestedVersion,
        ILocalizationService localizationService)
    {
        NodeInstanceId = nodeInstanceId;
        EffectivePolicy = effectivePolicy;
        Editor = new RuntimeFeedbackPolicyOverrideEditorViewModel(
            localizationService,
            draft);
        ActiveTaskCount = activeTasks.Count;
        var pendingCount = activeTasks.Count(
            task => task.RuntimeOptionsVersion < requestedVersion);
        ApplicationStatusText = activeTasks.Count == 0
            ? localizationService.GetString("run_runtime_options.node_inactive")
            : pendingCount > 0
                ? localizationService.Format(
                    "run_runtime_options.node_pending_format",
                    pendingCount,
                    activeTasks.Count)
                : localizationService.GetString("run_runtime_options.node_applied");
        EffectiveSummaryText = FormatPolicy(effectivePolicy, localizationService);
    }

    public string NodeInstanceId { get; }

    public ResolvedRuntimeFeedbackPolicyDto EffectivePolicy { get; }

    public RuntimeFeedbackPolicyOverrideEditorViewModel Editor { get; }

    public int ActiveTaskCount { get; }

    public string ApplicationStatusText { get; }

    public string EffectiveSummaryText { get; }

    internal static string FormatPolicy(
        ResolvedRuntimeFeedbackPolicyDto policy,
        ILocalizationService localizationService)
    {
        return localizationService.Format(
            "run_runtime_options.effective_policy_format",
            policy.Telemetry.LogLevel,
            policy.Telemetry.EventLevel,
            policy.Telemetry.ProgressEnabled
                ? localizationService.GetString("common.on")
                : localizationService.GetString("common.off"),
            policy.Telemetry.ProgressIntervalSeconds,
            policy.Diagnostics.IncludeMetrics
                ? localizationService.GetString("common.on")
                : localizationService.GetString("common.off"),
            policy.Diagnostics.PayloadByteLimit,
            policy.Diagnostics.MaskPolicy);
    }
}

public sealed class WorkflowRunRuntimeOptionsTaskViewModel : ViewModelBase
{
    public WorkflowRunRuntimeOptionsTaskViewModel(
        ActiveNodeTaskRuntimeOptionsVersionDto task,
        int requestedVersion,
        ILocalizationService localizationService)
    {
        TaskId = task.TaskId;
        NodeRunId = task.NodeRunId;
        NodeInstanceId = task.NodeInstanceId;
        NodeRunStatus = task.NodeRunStatus;
        RuntimeOptionsVersion = task.RuntimeOptionsVersion;
        IsApplied = task.RuntimeOptionsVersion >= requestedVersion;
        ApplicationStatusText = IsApplied
            ? localizationService.GetString("run_runtime_options.node_applied")
            : localizationService.GetString("run_runtime_options.node_pending");
    }

    public string TaskId { get; }

    public string NodeRunId { get; }

    public string NodeInstanceId { get; }

    public string NodeRunStatus { get; }

    public int RuntimeOptionsVersion { get; }

    public bool IsApplied { get; }

    public string ApplicationStatusText { get; }
}

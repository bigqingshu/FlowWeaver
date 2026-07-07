using System.Collections.Generic;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanApplyRuntimeOptionsDraft()
    {
        return HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict;
    }

    private bool CanResetRuntimeOptionsSelectedNodeOverride()
    {
        return CanApplyRuntimeOptionsDraft()
            && SelectedRuntimeOptionsNode is not null;
    }

    [RelayCommand(CanExecute = nameof(CanApplyRuntimeOptionsDraft))]
    private void ApplyRuntimeOptionsDraft()
    {
        if (IsRuntimeOptionsJsonEditorExpanded && IsRuntimeOptionsJsonDraftDirty)
        {
            ApplyRuntimeOptionsJsonDraft();
            return;
        }

        ApplyRuntimeOptionsStructuredDraft();
    }

    private void ApplyRuntimeOptionsStructuredDraft()
    {
        var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
        if (!readResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        if (!TryBuildRuntimeOptionsDraftFromStructuredInputs(
            readResult.Draft,
            out var draft,
            out var errorMessage))
        {
            RuntimeOptionsEditorErrorMessage = errorMessage;
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        ApplyRuntimeOptionsDraftToWorkflow(draft);
    }

    [RelayCommand(CanExecute = nameof(CanResetRuntimeOptionsSelectedNodeOverride))]
    private void ResetRuntimeOptionsSelectedNodeOverride()
    {
        if (SelectedRuntimeOptionsNode is null)
        {
            return;
        }

        var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
        if (!readResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        var nodeOverrides =
            new Dictionary<string, RuntimeOptionsNodeOverrideDraft>(
                readResult.Draft.NodeOverrides);
        nodeOverrides.Remove(SelectedRuntimeOptionsNode.NodeInstanceId);
        var draft = readResult.Draft with
        {
            NodeOverrides = nodeOverrides,
        };
        var patchResult = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            WorkflowDefinitionDraftJson,
            draft);
        if (!patchResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        RefreshSelectedRuntimeOptionsNodeDraftState(draft);
        RuntimeOptionsEditorErrorMessage = null;
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
        WorkflowDefinitionValidationMessage =
            T("definition.runtime_options_node_override_reset");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.runtime_options",
            UiNotificationKind.Success);
    }

    private bool TryBuildRuntimeOptionsDraftFromStructuredInputs(
        out RuntimeOptionsDraft draft,
        out string errorMessage)
    {
        var readResult = ReadWorkflowDefinitionDraftRuntimeOptionsFromCache();
        if (!readResult.Succeeded)
        {
            draft = new RuntimeOptionsDraft();
            errorMessage =
                LocalizeWorkflowDefinitionDraftWarning(readResult.Warning)
                ?? string.Empty;
            return false;
        }

        return TryBuildRuntimeOptionsDraftFromStructuredInputs(
            readResult.Draft,
            out draft,
            out errorMessage);
    }

    private bool TryBuildRuntimeOptionsDraftFromStructuredInputs(
        RuntimeOptionsDraft baseDraft,
        out RuntimeOptionsDraft draft,
        out string errorMessage)
    {
        draft = new RuntimeOptionsDraft();
        if (!TryBuildRuntimeOptionsWorkflowDraft(
            out var workflowDraft,
            out errorMessage))
        {
            return false;
        }

        var nodeOverrides =
            new Dictionary<string, RuntimeOptionsNodeOverrideDraft>(
                baseDraft.NodeOverrides);
        if (SelectedRuntimeOptionsNode is not null)
        {
            if (!TryBuildSelectedRuntimeOptionsNodeOverrideDraft(
                out var nodeOverride,
                out errorMessage))
            {
                return false;
            }

            nodeOverrides[SelectedRuntimeOptionsNode.NodeInstanceId] = nodeOverride;
        }

        draft = new RuntimeOptionsDraft
        {
            Version = RuntimeOptionsDefaults.Version,
            Workflow = workflowDraft,
            NodeOverrides = nodeOverrides,
        };
        return TryValidateRuntimeOptionsDraft(draft, out errorMessage);
    }

    private bool ApplyRuntimeOptionsDraftToWorkflow(RuntimeOptionsDraft draft)
    {
        var patchResult = WorkflowDefinitionDraftRuntimeOptionsPatcher.Apply(
            WorkflowDefinitionDraftJson,
            draft);
        if (!patchResult.Succeeded)
        {
            RuntimeOptionsEditorErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
            return false;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        RuntimeOptionsEditorErrorMessage = null;
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
        WorkflowDefinitionValidationMessage = T("definition.runtime_options_applied");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.runtime_options",
            UiNotificationKind.Success);
        if (IsRuntimeOptionsJsonEditorExpanded && !IsRuntimeOptionsJsonDraftDirty)
        {
            SetRuntimeOptionsJsonDraft(
                WorkflowDefinitionDraftRuntimeOptionsPatcher.FormatRuntimeOptions(draft),
                isDirty: false);
        }

        return true;
    }

    private bool TryBuildRuntimeOptionsWorkflowDraft(
        out RuntimeOptionsWorkflowDraft draft,
        out string errorMessage)
    {
        draft = new RuntimeOptionsWorkflowDraft();
        errorMessage = string.Empty;
        if (!TryParseNonNegativeInt(
            RuntimeOptionsEventRateLimitPerSecondDraft,
            RuntimeOptionsEventRateLimitText,
            out var eventRateLimit,
            out errorMessage) ||
            !TryParseNonNegativeDouble(
                RuntimeOptionsProgressIntervalSecondsDraft,
                RuntimeOptionsProgressIntervalText,
                out var progressInterval,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsPayloadByteLimitDraft,
                RuntimeOptionsPayloadByteLimitText,
                out var payloadByteLimit,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsTtlSecondsDraft,
                RuntimeOptionsTtlSecondsText,
                out var ttlSeconds,
                out errorMessage))
        {
            return false;
        }

        draft = new RuntimeOptionsWorkflowDraft
        {
            Profile = RuntimeOptionsProfileDraft,
            StrictValidation = RuntimeOptionsStrictValidationDraft,
            Telemetry = new RuntimeOptionsTelemetryDraft
            {
                LogLevel = RuntimeOptionsLogLevelDraft,
                EventLevel = RuntimeOptionsEventLevelDraft,
                EventRateLimitPerSecond = eventRateLimit,
                ProgressEnabled = RuntimeOptionsProgressEnabledDraft,
                ProgressIntervalSeconds = progressInterval,
            },
            Diagnostics = new RuntimeOptionsDiagnosticsDraft
            {
                CaptureErrorContext = RuntimeOptionsCaptureErrorContextDraft,
                IncludeMetrics = RuntimeOptionsIncludeMetricsDraft,
                PayloadByteLimit = payloadByteLimit,
                TtlSeconds = ttlSeconds,
                RedactColumns = RuntimeOptionsDraftStateMapper.ParseRedactColumns(
                    RuntimeOptionsRedactColumnsDraft),
                MaskPolicy = RuntimeOptionsMaskPolicyDraft,
            },
        };
        return true;
    }

    private bool TryBuildSelectedRuntimeOptionsNodeOverrideDraft(
        out RuntimeOptionsNodeOverrideDraft draft,
        out string errorMessage)
    {
        draft = new RuntimeOptionsNodeOverrideDraft();
        errorMessage = string.Empty;
        if (!TryParseNonNegativeInt(
            RuntimeOptionsSelectedNodeEventRateLimitPerSecondDraft,
            RuntimeOptionsEventRateLimitText,
            out var eventRateLimit,
            out errorMessage) ||
            !TryParseNonNegativeDouble(
                RuntimeOptionsSelectedNodeProgressIntervalSecondsDraft,
                RuntimeOptionsProgressIntervalText,
                out var progressInterval,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsSelectedNodePayloadByteLimitDraft,
                RuntimeOptionsPayloadByteLimitText,
                out var payloadByteLimit,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsSelectedNodeTtlSecondsDraft,
                RuntimeOptionsTtlSecondsText,
                out var ttlSeconds,
                out errorMessage))
        {
            return false;
        }

        draft = new RuntimeOptionsNodeOverrideDraft
        {
            Profile = RuntimeOptionsSelectedNodeProfileDraft,
            StrictValidation = RuntimeOptionsSelectedNodeStrictValidationDraft,
            Telemetry = new RuntimeOptionsTelemetryOverrideDraft
            {
                LogLevel = RuntimeOptionsSelectedNodeLogLevelDraft,
                EventLevel = RuntimeOptionsSelectedNodeEventLevelDraft,
                EventRateLimitPerSecond = eventRateLimit,
                ProgressEnabled = RuntimeOptionsSelectedNodeProgressEnabledDraft,
                ProgressIntervalSeconds = progressInterval,
            },
            Diagnostics = new RuntimeOptionsDiagnosticsOverrideDraft
            {
                CaptureErrorContext =
                    RuntimeOptionsSelectedNodeCaptureErrorContextDraft,
                IncludeMetrics = RuntimeOptionsSelectedNodeIncludeMetricsDraft,
                PayloadByteLimit = payloadByteLimit,
                TtlSeconds = ttlSeconds,
                RedactColumns = RuntimeOptionsDraftStateMapper.ParseRedactColumns(
                    RuntimeOptionsSelectedNodeRedactColumnsDraft),
                MaskPolicy = RuntimeOptionsSelectedNodeMaskPolicyDraft,
            },
        };
        return true;
    }
}

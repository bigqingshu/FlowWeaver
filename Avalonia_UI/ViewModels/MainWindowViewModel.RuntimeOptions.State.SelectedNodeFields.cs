using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyRuntimeOptionsSelectedNodeDraftFieldState(
        RuntimeOptionsNodeDraftFieldState selectedNodeFieldState)
    {
        RuntimeOptionsSelectedNodeProfileDraft =
            selectedNodeFieldState.Profile ?? RuntimeOptionsDefaults.Profile;
        RuntimeOptionsSelectedNodeStrictValidationDraft =
            selectedNodeFieldState.StrictValidation ?? true;
        RuntimeOptionsSelectedNodeLogLevelDraft =
            selectedNodeFieldState.LogLevel ?? RuntimeOptionsDefaults.LogLevel;
        RuntimeOptionsSelectedNodeEventLevelDraft =
            selectedNodeFieldState.EventLevel ?? RuntimeOptionsDefaults.EventLevel;
        RuntimeOptionsSelectedNodeEventRateLimitPerSecondDraft =
            selectedNodeFieldState.EventRateLimitPerSecond ?? "0";
        RuntimeOptionsSelectedNodeProgressEnabledDraft =
            selectedNodeFieldState.ProgressEnabled ?? true;
        RuntimeOptionsSelectedNodeProgressIntervalSecondsDraft =
            selectedNodeFieldState.ProgressIntervalSeconds ?? "0";
        RuntimeOptionsSelectedNodeCaptureErrorContextDraft =
            selectedNodeFieldState.CaptureErrorContext ?? true;
        RuntimeOptionsSelectedNodeIncludeMetricsDraft =
            selectedNodeFieldState.IncludeMetrics ?? true;
        RuntimeOptionsSelectedNodePayloadByteLimitDraft =
            selectedNodeFieldState.PayloadByteLimit ?? "0";
        RuntimeOptionsSelectedNodeTtlSecondsDraft =
            selectedNodeFieldState.TtlSeconds ?? "0";
        RuntimeOptionsSelectedNodeRedactColumnsDraft =
            selectedNodeFieldState.RedactColumns ?? string.Empty;
        RuntimeOptionsSelectedNodeMaskPolicyDraft =
            selectedNodeFieldState.MaskPolicy ?? RuntimeOptionsDefaults.MaskPolicy;
    }
}

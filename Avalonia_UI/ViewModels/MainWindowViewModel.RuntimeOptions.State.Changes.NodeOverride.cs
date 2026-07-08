using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private WorkflowDefinitionNodeListItemViewModel? selectedRuntimeOptionsNode;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeProfileDraft = RuntimeOptionsDefaults.Profile;

    [ObservableProperty]
    private bool runtimeOptionsSelectedNodeStrictValidationDraft = true;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeLogLevelDraft =
        RuntimeOptionsDefaults.LogLevel;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeEventLevelDraft =
        RuntimeOptionsDefaults.EventLevel;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeEventRateLimitPerSecondDraft = "0";

    [ObservableProperty]
    private bool runtimeOptionsSelectedNodeProgressEnabledDraft = true;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeProgressIntervalSecondsDraft = "0";

    [ObservableProperty]
    private bool runtimeOptionsSelectedNodeCaptureErrorContextDraft = true;

    [ObservableProperty]
    private bool runtimeOptionsSelectedNodeIncludeMetricsDraft = true;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodePayloadByteLimitDraft = "0";

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeTtlSecondsDraft = "0";

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeRedactColumnsDraft = string.Empty;

    [ObservableProperty]
    private string runtimeOptionsSelectedNodeMaskPolicyDraft =
        RuntimeOptionsDefaults.MaskPolicy;
}

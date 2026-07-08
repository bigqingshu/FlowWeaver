using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static readonly string[] RuntimeOptionsProfileValues =
        ["normal", "background_fast", "diagnostic", "custom"];
    private static readonly string[] RuntimeOptionsLogLevelValues =
        ["DEBUG", "INFO", "WARN", "ERROR"];
    private static readonly string[] RuntimeOptionsEventLevelValues =
        ["none", "basic", "progress", "verbose"];
    private static readonly string[] RuntimeOptionsMaskPolicyValues =
        ["none", "partial", "full"];

    public IReadOnlyList<NodeConfigOptionItemViewModel> RuntimeOptionsProfileOptions =>
        CreateRuntimeOptionsOptions("profile", RuntimeOptionsProfileValues);

    public IReadOnlyList<NodeConfigOptionItemViewModel> RuntimeOptionsLogLevelOptions =>
        CreateRuntimeOptionsOptions("log_level", RuntimeOptionsLogLevelValues);

    public IReadOnlyList<NodeConfigOptionItemViewModel> RuntimeOptionsEventLevelOptions =>
        CreateRuntimeOptionsOptions("event_level", RuntimeOptionsEventLevelValues);

    public IReadOnlyList<NodeConfigOptionItemViewModel> RuntimeOptionsMaskPolicyOptions =>
        CreateRuntimeOptionsOptions("mask_policy", RuntimeOptionsMaskPolicyValues);

    public bool HasSelectedRuntimeOptionsNode => SelectedRuntimeOptionsNode is not null;

    public bool HasRuntimeOptionsEditorError =>
        !string.IsNullOrWhiteSpace(RuntimeOptionsEditorErrorMessage);

    public string RuntimeOptionsSummaryText =>
        F(
            "definition.runtime_options_summary",
            FormatRuntimeOptionsOptionValue("profile", RuntimeOptionsProfileDraft),
            FormatRuntimeOptionsOptionValue("event_level", RuntimeOptionsEventLevelDraft),
            RuntimeOptionsProgressEnabledDraft ? T("common.on") : T("common.off"),
            RuntimeOptionsNodeOverrideCount);

    public bool HasSelectedRunRuntimeOptionsSummary => SelectedRun is not null;

    public string SelectedRunRuntimeOptionsSummaryText =>
        FormatSelectedRunRuntimeOptionsSummary();

    public string RuntimeOptionsSectionText => T("definition.runtime_options");

    public string RuntimeOptionsOpenEditorText =>
        T("definition.runtime_options_open_editor");

    public string RuntimeOptionsWindowTitleText =>
        T("definition.runtime_options_window_title");

    public string RuntimeOptionsWorkflowSectionText =>
        T("definition.runtime_options_workflow_section");

    public string RuntimeOptionsNodeOverrideSectionText =>
        T("definition.runtime_options_node_override_section");

    public string RuntimeOptionsProfileText => T("definition.runtime_options_profile");

    public string RuntimeOptionsStrictValidationText =>
        T("definition.runtime_options_strict_validation");

    public string RuntimeOptionsLogLevelText => T("definition.runtime_options_log_level");

    public string RuntimeOptionsEventLevelText =>
        T("definition.runtime_options_event_level");

    public string RuntimeOptionsEventRateLimitText =>
        T("definition.runtime_options_event_rate_limit");

    public string RuntimeOptionsProgressEnabledText =>
        T("definition.runtime_options_progress_enabled");

    public string RuntimeOptionsProgressIntervalText =>
        T("definition.runtime_options_progress_interval");

    public string RuntimeOptionsCaptureErrorContextText =>
        T("definition.runtime_options_capture_error_context");

    public string RuntimeOptionsIncludeMetricsText =>
        T("definition.runtime_options_include_metrics");

    public string RuntimeOptionsPayloadByteLimitText =>
        T("definition.runtime_options_payload_byte_limit");

    public string RuntimeOptionsTtlSecondsText =>
        T("definition.runtime_options_ttl_seconds");

    public string RuntimeOptionsRedactColumnsText =>
        T("definition.runtime_options_redact_columns");

    public string RuntimeOptionsMaskPolicyText =>
        T("definition.runtime_options_mask_policy");

    public string RuntimeOptionsSelectNodeText =>
        T("definition.runtime_options_select_node");

    public string RuntimeOptionsApplyText => T("definition.runtime_options_apply");

    public string RuntimeOptionsResetNodeOverrideText =>
        T("definition.runtime_options_reset_node_override");

    private void NotifyRuntimeOptionsSummaryChanged()
    {
        OnPropertyChanged(nameof(RuntimeOptionsSummaryText));
    }

    private IReadOnlyList<NodeConfigOptionItemViewModel> CreateRuntimeOptionsOptions(
        string group,
        IReadOnlyList<string> values)
    {
        return values
            .Select(value => new NodeConfigOptionItemViewModel(
                value,
                FormatRuntimeOptionsOptionValue(group, value)))
            .ToArray();
    }

    private string FormatRuntimeOptionsOptionValue(string group, string value)
    {
        return DisplayTextFormatter.FormatRuntimeOptionsOptionValue(group, value);
    }
}

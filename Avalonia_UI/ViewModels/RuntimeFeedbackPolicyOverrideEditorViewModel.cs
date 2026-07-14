using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public sealed record RuntimeOptionsChoiceViewModel(string? Value, string DisplayText);

public sealed partial class RuntimeFeedbackPolicyOverrideEditorViewModel : ViewModelBase
{
    private readonly ILocalizationService localizationService;

    [ObservableProperty]
    private RuntimeOptionsChoiceViewModel? selectedLogLevel;

    [ObservableProperty]
    private RuntimeOptionsChoiceViewModel? selectedEventLevel;

    [ObservableProperty]
    private RuntimeOptionsChoiceViewModel? selectedMaskPolicy;

    [ObservableProperty]
    private string eventRateLimitDraft = string.Empty;

    [ObservableProperty]
    private bool? progressEnabled;

    [ObservableProperty]
    private string progressIntervalDraft = string.Empty;

    [ObservableProperty]
    private bool? captureErrorContext;

    [ObservableProperty]
    private bool? includeMetrics;

    [ObservableProperty]
    private string payloadByteLimitDraft = string.Empty;

    [ObservableProperty]
    private bool overrideRedactColumns;

    [ObservableProperty]
    private string redactColumnsDraft = string.Empty;

    public RuntimeFeedbackPolicyOverrideEditorViewModel(
        ILocalizationService localizationService,
        RuntimeFeedbackPolicyOverrideDraft? draft = null)
    {
        this.localizationService = localizationService;
        LogLevelOptions = BuildOptions(
            ["DEBUG", "INFO", "WARN", "ERROR"],
            "runtime_options.log_level.option.");
        EventLevelOptions = BuildOptions(
            ["none", "basic", "progress", "verbose"],
            "runtime_options.event_level.option.");
        MaskPolicyOptions = BuildOptions(
            ["none", "partial", "full"],
            "runtime_options.mask_policy.option.");
        Load(draft ?? new RuntimeFeedbackPolicyOverrideDraft());
    }

    public IReadOnlyList<RuntimeOptionsChoiceViewModel> LogLevelOptions { get; }

    public IReadOnlyList<RuntimeOptionsChoiceViewModel> EventLevelOptions { get; }

    public IReadOnlyList<RuntimeOptionsChoiceViewModel> MaskPolicyOptions { get; }

    public string LogLevelText => T("definition.runtime_options_log_level");

    public string EventLevelText => T("definition.runtime_options_event_level");

    public string EventRateLimitText => T("definition.runtime_options_event_rate_limit");

    public string ProgressEnabledText => T("definition.runtime_options_progress_enabled");

    public string ProgressIntervalText => T("definition.runtime_options_progress_interval");

    public string CaptureErrorContextText => T("definition.runtime_options_capture_error_context");

    public string IncludeMetricsText => T("definition.runtime_options_include_metrics");

    public string PayloadByteLimitText => T("definition.runtime_options_payload_byte_limit");

    public string RedactColumnsText => T("definition.runtime_options_redact_columns");

    public string MaskPolicyText => T("definition.runtime_options_mask_policy");

    public string ResetText => T("run_runtime_options.reset_scope");

    public string InheritText => T("run_runtime_options.inherit");

    public string ProgressEnabledOverrideText => FormatOptionalBoolean(ProgressEnabled);

    public string CaptureErrorContextOverrideText => FormatOptionalBoolean(CaptureErrorContext);

    public string IncludeMetricsOverrideText => FormatOptionalBoolean(IncludeMetrics);

    public bool TryBuild(
        out RuntimeFeedbackPolicyOverrideDraft draft,
        out string? validationError)
    {
        if (!TryParseOptionalInt(EventRateLimitDraft, EventRateLimitText, out var eventRate, out validationError)
            || !TryParseOptionalDouble(ProgressIntervalDraft, ProgressIntervalText, out var progressInterval, out validationError)
            || !TryParseOptionalInt(PayloadByteLimitDraft, PayloadByteLimitText, out var payloadLimit, out validationError))
        {
            draft = new RuntimeFeedbackPolicyOverrideDraft();
            return false;
        }

        draft = new RuntimeFeedbackPolicyOverrideDraft
        {
            LogLevel = SelectedLogLevel?.Value,
            EventLevel = SelectedEventLevel?.Value,
            EventRateLimitPerSecond = eventRate,
            ProgressEnabled = ProgressEnabled,
            ProgressIntervalSeconds = progressInterval,
            CaptureErrorContext = CaptureErrorContext,
            IncludeMetrics = IncludeMetrics,
            PayloadByteLimit = payloadLimit,
            RedactColumns = OverrideRedactColumns
                ? (RedactColumnsDraft ?? string.Empty)
                    .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
                    .Distinct(StringComparer.Ordinal)
                    .ToArray()
                : null,
            MaskPolicy = SelectedMaskPolicy?.Value,
        };
        validationError = null;
        return true;
    }

    public void Load(RuntimeFeedbackPolicyOverrideDraft draft)
    {
        SelectedLogLevel = FindOption(LogLevelOptions, draft.LogLevel);
        SelectedEventLevel = FindOption(EventLevelOptions, draft.EventLevel);
        SelectedMaskPolicy = FindOption(MaskPolicyOptions, draft.MaskPolicy);
        EventRateLimitDraft = FormatOptional(draft.EventRateLimitPerSecond);
        ProgressEnabled = draft.ProgressEnabled;
        ProgressIntervalDraft = FormatOptional(draft.ProgressIntervalSeconds);
        CaptureErrorContext = draft.CaptureErrorContext;
        IncludeMetrics = draft.IncludeMetrics;
        PayloadByteLimitDraft = FormatOptional(draft.PayloadByteLimit);
        OverrideRedactColumns = draft.RedactColumns is not null;
        RedactColumnsDraft = draft.RedactColumns is null
            ? string.Empty
            : string.Join(", ", draft.RedactColumns);
    }

    [RelayCommand]
    private void Reset()
    {
        Load(new RuntimeFeedbackPolicyOverrideDraft());
    }

    private IReadOnlyList<RuntimeOptionsChoiceViewModel> BuildOptions(
        IReadOnlyList<string> values,
        string localizationPrefix)
    {
        var result = new List<RuntimeOptionsChoiceViewModel>
        {
            new(null, InheritText),
        };
        result.AddRange(
            values.Select(value => new RuntimeOptionsChoiceViewModel(
                value,
                T(localizationPrefix + value))));
        return result;
    }

    private static RuntimeOptionsChoiceViewModel FindOption(
        IReadOnlyList<RuntimeOptionsChoiceViewModel> options,
        string? value)
    {
        return options.First(option => string.Equals(option.Value, value, StringComparison.Ordinal));
    }

    private bool TryParseOptionalInt(
        string value,
        string fieldName,
        out int? parsed,
        out string? validationError)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            parsed = null;
            validationError = null;
            return true;
        }

        if (int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out var number)
            && number >= 0)
        {
            parsed = number;
            validationError = null;
            return true;
        }

        parsed = null;
        validationError = localizationService.Format(
            "definition.runtime_options_number_invalid",
            fieldName);
        return false;
    }

    private bool TryParseOptionalDouble(
        string value,
        string fieldName,
        out double? parsed,
        out string? validationError)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            parsed = null;
            validationError = null;
            return true;
        }

        if (double.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out var number)
            && double.IsFinite(number)
            && number >= 0)
        {
            parsed = number;
            validationError = null;
            return true;
        }

        parsed = null;
        validationError = localizationService.Format(
            "definition.runtime_options_number_invalid",
            fieldName);
        return false;
    }

    private string T(string key) => localizationService.GetString(key);

    private string FormatOptionalBoolean(bool? value)
    {
        return value switch
        {
            true => T("common.on"),
            false => T("common.off"),
            null => InheritText,
        };
    }

    private static string FormatOptional<T>(T? value)
        where T : struct, IFormattable
    {
        return value?.ToString(null, CultureInfo.InvariantCulture) ?? string.Empty;
    }

    partial void OnProgressEnabledChanged(bool? value)
    {
        OnPropertyChanged(nameof(ProgressEnabledOverrideText));
    }

    partial void OnCaptureErrorContextChanged(bool? value)
    {
        OnPropertyChanged(nameof(CaptureErrorContextOverrideText));
    }

    partial void OnIncludeMetricsChanged(bool? value)
    {
        OnPropertyChanged(nameof(IncludeMetricsOverrideText));
    }
}

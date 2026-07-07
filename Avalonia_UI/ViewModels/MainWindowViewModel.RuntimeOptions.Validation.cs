using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool TryValidateRuntimeOptionsDraft(
        RuntimeOptionsDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsWorkflowDraft(draft.Workflow, out errorMessage))
        {
            return false;
        }

        foreach (var nodeOverride in draft.NodeOverrides.Values)
        {
            if (!TryValidateRuntimeOptionsNodeOverrideDraft(
                nodeOverride,
                out errorMessage))
            {
                return false;
            }
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsWorkflowDraft(
        RuntimeOptionsWorkflowDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsOption(
            RuntimeOptionsProfileValues,
            draft.Profile,
            RuntimeOptionsProfileText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsTelemetryDraft(
                draft.Telemetry,
                out errorMessage) ||
            !TryValidateRuntimeOptionsDiagnosticsDraft(
                draft.Diagnostics,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsTelemetryDraft(
        RuntimeOptionsTelemetryDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsOption(
            RuntimeOptionsLogLevelValues,
            draft.LogLevel,
            RuntimeOptionsLogLevelText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsOption(
                RuntimeOptionsEventLevelValues,
                draft.EventLevel,
                RuntimeOptionsEventLevelText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.EventRateLimitPerSecond,
                RuntimeOptionsEventRateLimitText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.ProgressIntervalSeconds,
                RuntimeOptionsProgressIntervalText,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsDiagnosticsDraft(
        RuntimeOptionsDiagnosticsDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsNonNegative(
            draft.PayloadByteLimit,
            RuntimeOptionsPayloadByteLimitText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.TtlSeconds,
                RuntimeOptionsTtlSecondsText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsOption(
                RuntimeOptionsMaskPolicyValues,
                draft.MaskPolicy,
                RuntimeOptionsMaskPolicyText,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsNodeOverrideDraft(
        RuntimeOptionsNodeOverrideDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsOption(
            RuntimeOptionsProfileValues,
            draft.Profile,
            RuntimeOptionsProfileText,
            out errorMessage))
        {
            return false;
        }

        if (draft.Telemetry is not null &&
            !TryValidateRuntimeOptionsTelemetryOverrideDraft(
                draft.Telemetry,
                out errorMessage))
        {
            return false;
        }

        if (draft.Diagnostics is not null &&
            !TryValidateRuntimeOptionsDiagnosticsOverrideDraft(
                draft.Diagnostics,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsTelemetryOverrideDraft(
        RuntimeOptionsTelemetryOverrideDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsOption(
            RuntimeOptionsLogLevelValues,
            draft.LogLevel,
            RuntimeOptionsLogLevelText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsOption(
                RuntimeOptionsEventLevelValues,
                draft.EventLevel,
                RuntimeOptionsEventLevelText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.EventRateLimitPerSecond,
                RuntimeOptionsEventRateLimitText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.ProgressIntervalSeconds,
                RuntimeOptionsProgressIntervalText,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsDiagnosticsOverrideDraft(
        RuntimeOptionsDiagnosticsOverrideDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsNonNegative(
            draft.PayloadByteLimit,
            RuntimeOptionsPayloadByteLimitText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.TtlSeconds,
                RuntimeOptionsTtlSecondsText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsOption(
                RuntimeOptionsMaskPolicyValues,
                draft.MaskPolicy,
                RuntimeOptionsMaskPolicyText,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsOption(
        IReadOnlyList<string> options,
        string? value,
        string label,
        out string errorMessage)
    {
        if (value is null || options.Contains(value, StringComparer.Ordinal))
        {
            errorMessage = string.Empty;
            return true;
        }

        errorMessage = F("definition.runtime_options_value_invalid", label);
        return false;
    }

    private bool TryValidateRuntimeOptionsNonNegative(
        int? value,
        string label,
        out string errorMessage)
    {
        if (!value.HasValue || value.Value >= 0)
        {
            errorMessage = string.Empty;
            return true;
        }

        errorMessage = F("definition.runtime_options_number_invalid", label);
        return false;
    }

    private bool TryValidateRuntimeOptionsNonNegative(
        double? value,
        string label,
        out string errorMessage)
    {
        if (!value.HasValue || value.Value >= 0)
        {
            errorMessage = string.Empty;
            return true;
        }

        errorMessage = F("definition.runtime_options_number_invalid", label);
        return false;
    }

    private bool TryParseNonNegativeInt(
        string input,
        string label,
        out int value,
        out string errorMessage)
    {
        if (int.TryParse(
            input,
            NumberStyles.Integer,
            CultureInfo.InvariantCulture,
            out value) &&
            value >= 0)
        {
            errorMessage = string.Empty;
            return true;
        }

        errorMessage = F("definition.runtime_options_number_invalid", label);
        return false;
    }

    private bool TryParseNonNegativeDouble(
        string input,
        string label,
        out double value,
        out string errorMessage)
    {
        if (double.TryParse(
            input,
            NumberStyles.Float,
            CultureInfo.InvariantCulture,
            out value) &&
            value >= 0)
        {
            errorMessage = string.Empty;
            return true;
        }

        errorMessage = F("definition.runtime_options_number_invalid", label);
        return false;
    }
}

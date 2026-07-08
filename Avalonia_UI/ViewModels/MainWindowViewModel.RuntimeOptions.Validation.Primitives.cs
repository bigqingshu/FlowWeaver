using System;
using System.Collections.Generic;
using System.Linq;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}

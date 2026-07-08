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

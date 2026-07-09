using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}

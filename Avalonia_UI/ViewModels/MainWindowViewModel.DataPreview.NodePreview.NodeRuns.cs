using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static NodeRunDto? FindNodeRunByInstanceId(
        IEnumerable<NodeRunDto> nodeRuns,
        string nodeInstanceId)
    {
        return nodeRuns.FirstOrDefault(item =>
            string.Equals(
                item.NodeInstanceId,
                nodeInstanceId,
                StringComparison.Ordinal));
    }
}

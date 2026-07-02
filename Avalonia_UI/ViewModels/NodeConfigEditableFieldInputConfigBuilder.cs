using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public static class NodeConfigEditableFieldInputConfigBuilder
{
    public static NodeConfigEditableDraftConfigResult Build(
        string nodeInstanceId,
        IEnumerable<NodeConfigEditableFieldInputViewModel> fields)
    {
        var draft = new NodeConfigEditableDraft
        {
            NodeInstanceId = nodeInstanceId,
            Fields = fields
                .Select(field => field.ToEditableDraftField())
                .ToArray(),
        };

        return NodeConfigEditableDraftConfigBuilder.Build(draft);
    }
}

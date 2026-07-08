using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private string? FormatRemovedConnectionsMessage(
        IReadOnlyList<WorkflowDefinitionDraftConnection> removedConnections)
    {
        if (removedConnections.Count == 0)
        {
            return null;
        }

        return F(
            "definition.node_delete_removed_connections",
            string.Join(
                Environment.NewLine,
                removedConnections.Select(FormatRelatedConnectionSummary)));
    }

}

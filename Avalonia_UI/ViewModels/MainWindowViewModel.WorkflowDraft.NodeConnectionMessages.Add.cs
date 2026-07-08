using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private string? FormatAutoWiredConnectionsMessage(
        IReadOnlyList<WorkflowDefinitionDraftConnection> removedConnections,
        IReadOnlyList<WorkflowDefinitionDraftConnection> addedConnections)
    {
        if (removedConnections.Count == 0 && addedConnections.Count == 0)
        {
            return null;
        }

        var removedText = removedConnections.Count == 0
            ? "-"
            : string.Join(
                Environment.NewLine,
                removedConnections.Select(FormatRelatedConnectionSummary));
        var addedText = addedConnections.Count == 0
            ? "-"
            : string.Join(
                Environment.NewLine,
                addedConnections.Select(FormatRelatedConnectionSummary));

        return F(
            "definition.node_add_rewired_connections",
            removedText,
            addedText);
    }
}

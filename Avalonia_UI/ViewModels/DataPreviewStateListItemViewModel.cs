using System;
using System.Collections.Generic;
using System.Linq;

namespace Avalonia_UI.ViewModels;

public sealed class DataPreviewStateListItemViewModel
{
    private const string ReadCapability = "READ";

    public DataPreviewStateListItemViewModel(
        string workflowRunId,
        string nodeRunId,
        IEnumerable<TableRefListItemViewModel> tableRefs)
    {
        WorkflowRunId = RequireValue(workflowRunId, nameof(workflowRunId));
        NodeRunId = RequireValue(nodeRunId, nameof(nodeRunId));
        TableRefs = tableRefs.ToArray();
        if (TableRefs.Count == 0)
        {
            throw new ArgumentException("A data preview state requires at least one table ref.", nameof(tableRefs));
        }

        foreach (var tableRef in TableRefs)
        {
            if (!string.Equals(tableRef.WorkflowRunId, WorkflowRunId, StringComparison.Ordinal)
                || !string.Equals(tableRef.NodeRunId, NodeRunId, StringComparison.Ordinal))
            {
                throw new ArgumentException(
                    "All table refs in a data preview state must share the same workflow run and node run.",
                    nameof(tableRefs));
            }
        }
    }

    public string WorkflowRunId { get; }

    public string NodeRunId { get; }

    public IReadOnlyList<TableRefListItemViewModel> TableRefs { get; }

    public string StateKey => $"{WorkflowRunId}:{NodeRunId}";

    public string DisplayText => NodeRunId;

    public int TableCount => TableRefs.Count;

    public string TableCountText => $"{TableCount} table(s)";

    public int ReadableTableCount =>
        TableRefs.Count(tableRef => tableRef.HasCapability(ReadCapability));

    public bool HasReadableTables => ReadableTableCount > 0;

    public string StorageKindsText =>
        string.Join(
            ", ",
            TableRefs
                .Select(tableRef => tableRef.StorageKind)
                .Where(storageKind => !string.IsNullOrWhiteSpace(storageKind))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .OrderBy(storageKind => storageKind, StringComparer.OrdinalIgnoreCase));

    public string SummaryText =>
        string.IsNullOrWhiteSpace(StorageKindsText)
            ? TableCountText
            : $"{TableCountText} · {StorageKindsText}";

    public static IReadOnlyList<DataPreviewStateListItemViewModel> FromTableRefs(
        IEnumerable<TableRefListItemViewModel> tableRefs)
    {
        var groups = new List<(string WorkflowRunId, string NodeRunId, List<TableRefListItemViewModel> TableRefs)>();
        foreach (var tableRef in tableRefs)
        {
            var group = groups.FirstOrDefault(item =>
                string.Equals(item.WorkflowRunId, tableRef.WorkflowRunId, StringComparison.Ordinal)
                && string.Equals(item.NodeRunId, tableRef.NodeRunId, StringComparison.Ordinal));
            if (group.TableRefs is null)
            {
                groups.Add((tableRef.WorkflowRunId, tableRef.NodeRunId, [tableRef]));
                continue;
            }

            group.TableRefs.Add(tableRef);
        }

        return groups
            .Select(group => new DataPreviewStateListItemViewModel(
                group.WorkflowRunId,
                group.NodeRunId,
                group.TableRefs))
            .ToArray();
    }

    private static string RequireValue(string value, string parameterName)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new ArgumentException("Value cannot be empty.", parameterName);
        }

        return value;
    }
}

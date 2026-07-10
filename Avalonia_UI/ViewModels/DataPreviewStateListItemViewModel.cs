using System;
using System.Collections.Generic;
using System.Linq;

namespace Avalonia_UI.ViewModels;

public sealed class DataPreviewStateListItemViewModel : ViewModelBase
{
    private readonly Func<string, string> translate;

    public DataPreviewStateListItemViewModel(
        string workflowRunId,
        string nodeRunId,
        string tableType,
        IEnumerable<TableRefListItemViewModel> tableRefs,
        Func<string, string>? translate = null)
    {
        this.translate = translate ?? DefaultText;
        WorkflowRunId = RequireValue(workflowRunId, nameof(workflowRunId));
        NodeRunId = RequireValue(nodeRunId, nameof(nodeRunId));
        TableType = RequireValue(tableType, nameof(tableType));
        TableRefs = tableRefs.ToArray();
        if (TableRefs.Count == 0)
        {
            throw new ArgumentException("A data preview state requires at least one table ref.", nameof(tableRefs));
        }

        foreach (var tableRef in TableRefs)
        {
            if (!string.Equals(tableRef.WorkflowRunId, WorkflowRunId, StringComparison.Ordinal)
                || !string.Equals(tableRef.NodeRunId, NodeRunId, StringComparison.Ordinal)
                || !string.Equals(tableRef.TableType, TableType, StringComparison.Ordinal))
            {
                throw new ArgumentException(
                    "All table refs in a data preview state must share the same workflow run, node run, and table type.",
                    nameof(tableRefs));
            }
        }

        SourceNodeInstanceId = TableRefs
            .Select(tableRef => tableRef.SourceNodeInstanceId)
            .FirstOrDefault(value => !string.IsNullOrWhiteSpace(value));
    }

    public string WorkflowRunId { get; }

    public string NodeRunId { get; }

    public string TableType { get; }

    public string? SourceNodeInstanceId { get; }

    public IReadOnlyList<TableRefListItemViewModel> TableRefs { get; }

    public string StateKey => $"{WorkflowRunId}:{NodeRunId}:{TableType}";

    public string DisplayText =>
        $"{(string.IsNullOrWhiteSpace(SourceNodeInstanceId) ? NodeRunId : SourceNodeInstanceId)} | {TableTypeText}";

    public string TableTypeText => translate($"data_preview.table_type.{TableType}");

    public int TableCount => TableRefs.Count;

    public string TableCountText => $"{TableCount} table(s)";

    public int ReadableTableCount =>
        TableRefs.Count(tableRef => tableRef.CanReadRows);

    public int UnreadableTableCount => TableCount - ReadableTableCount;

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
            : $"{TableCountText} · {ReadableTableCount} {translate("data_preview.readable")} · {StorageKindsText}";

    public static IReadOnlyList<DataPreviewStateListItemViewModel> FromTableRefs(
        IEnumerable<TableRefListItemViewModel> tableRefs,
        Func<string, string>? translate = null)
    {
        var groups = new List<(
            string WorkflowRunId,
            string NodeRunId,
            string TableType,
            List<TableRefListItemViewModel> TableRefs)>();
        foreach (var tableRef in tableRefs)
        {
            var group = groups.FirstOrDefault(item =>
                string.Equals(item.WorkflowRunId, tableRef.WorkflowRunId, StringComparison.Ordinal)
                && string.Equals(item.NodeRunId, tableRef.NodeRunId, StringComparison.Ordinal)
                && string.Equals(item.TableType, tableRef.TableType, StringComparison.Ordinal));
            if (group.TableRefs is null)
            {
                groups.Add((
                    tableRef.WorkflowRunId,
                    tableRef.NodeRunId,
                    tableRef.TableType,
                    [tableRef]));
                continue;
            }

            group.TableRefs.Add(tableRef);
        }

        return groups
            .OrderBy(group => TableTypeOrder(group.TableType))
            .ThenBy(group => group.WorkflowRunId, StringComparer.Ordinal)
            .ThenBy(group => group.NodeRunId, StringComparer.Ordinal)
            .Select(group => new DataPreviewStateListItemViewModel(
                group.WorkflowRunId,
                group.NodeRunId,
                group.TableType,
                group.TableRefs,
                translate))
            .ToArray();
    }

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(DisplayText));
        OnPropertyChanged(nameof(TableTypeText));
        OnPropertyChanged(nameof(SummaryText));
    }

    private static int TableTypeOrder(string tableType)
    {
        return tableType switch
        {
            "current_table" => 0,
            "memory_table" => 1,
            "runtime_sql_table" => 2,
            "external_sql_table" => 3,
            _ => 4,
        };
    }

    private static string DefaultText(string key)
    {
        return key switch
        {
            "data_preview.table_type.current_table" => "Current table",
            "data_preview.table_type.memory_table" => "Memory table",
            "data_preview.table_type.runtime_sql_table" => "Runtime SQL table",
            "data_preview.table_type.external_sql_table" => "External SQL reference",
            "data_preview.readable" => "readable",
            _ => key,
        };
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

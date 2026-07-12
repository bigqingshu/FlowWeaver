using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static bool IsReadableTableRef(TableRefDto tableRef)
    {
        return tableRef.CanReadRows;
    }

    private static RunTableDirectoryItemDto? FindLatestReadableNodeTableRef(
        IEnumerable<RunTableDirectoryItemDto> tableRefs,
        string sourceNodeInstanceId)
    {
        return tableRefs
            .Where(item =>
                LogicalResultNodeInstanceIds(item).Contains(
                    sourceNodeInstanceId,
                    StringComparer.Ordinal)
                && IsReadableTableRef(item))
            .OrderByDescending(item => item.Version)
            .ThenByDescending(item => item.CreatedAt)
            .FirstOrDefault();
    }

    private static IEnumerable<string> LogicalResultNodeInstanceIds(
        RunTableDirectoryItemDto tableRef)
    {
        if (tableRef.ResultBindings.Length > 0)
        {
            return tableRef.ResultBindings
                .Select(binding => binding.NodeInstanceId)
                .Where(nodeInstanceId => !string.IsNullOrWhiteSpace(nodeInstanceId));
        }

        return string.IsNullOrWhiteSpace(tableRef.SourceNodeInstanceId)
            ? []
            : [tableRef.SourceNodeInstanceId];
    }
}

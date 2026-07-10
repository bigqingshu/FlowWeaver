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

    private static TableRefDto? FindLatestReadableNodeTableRef(
        IEnumerable<TableRefDto> tableRefs,
        string sourceNodeInstanceId)
    {
        return tableRefs
            .Where(item =>
                string.Equals(
                    item.SourceNodeInstanceId,
                    sourceNodeInstanceId,
                    StringComparison.Ordinal)
                && IsReadableTableRef(item))
            .OrderByDescending(item => item.Version)
            .ThenByDescending(item => item.CreatedAt)
            .FirstOrDefault();
    }
}

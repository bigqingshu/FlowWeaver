using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static bool IsReadablePublishedTableRef(TableRefDto tableRef)
    {
        return string.Equals(
                tableRef.LifecycleStatus,
                "PUBLISHED",
                StringComparison.OrdinalIgnoreCase)
            && tableRef.Capabilities.Any(capability =>
                string.Equals(capability, "READ", StringComparison.OrdinalIgnoreCase));
    }

    private static TableRefDto? FindLatestReadableNodeRunTableRef(
        IEnumerable<TableRefDto> tableRefs,
        string nodeRunId)
    {
        return tableRefs
            .Where(item =>
                string.Equals(item.NodeRunId, nodeRunId, StringComparison.Ordinal)
                && IsReadablePublishedTableRef(item))
            .OrderByDescending(item => item.Version)
            .ThenByDescending(item => item.CreatedAt)
            .FirstOrDefault();
    }
}

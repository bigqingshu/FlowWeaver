using System;
using System.Linq;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class TableRefListItemViewModel
{
    public TableRefListItemViewModel(TableRefDto tableRef)
    {
        TableRefId = tableRef.TableRefId;
        WorkflowRunId = tableRef.WorkflowRunId;
        NodeRunId = tableRef.NodeRunId;
        Role = tableRef.Role;
        StorageKind = tableRef.StorageKind;
        Scope = tableRef.Scope;
        Mutability = tableRef.Mutability;
        ProviderId = tableRef.ProviderId;
        LogicalTableId = tableRef.LogicalTableId;
        Version = tableRef.Version;
        Capabilities = tableRef.Capabilities;
        LifecycleStatus = tableRef.LifecycleStatus;
        CreatedAt = tableRef.CreatedAt;
    }

    public string TableRefId { get; }

    public string WorkflowRunId { get; }

    public string NodeRunId { get; }

    public string Role { get; }

    public string StorageKind { get; }

    public string Scope { get; }

    public string Mutability { get; }

    public string ProviderId { get; }

    public string LogicalTableId { get; }

    public int Version { get; }

    public string[] Capabilities { get; }

    public string LifecycleStatus { get; }

    public DateTimeOffset CreatedAt { get; }

    public string VersionText => $"v{Version}";

    public string CreatedAtText => CreatedAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss");

    public string CapabilitiesText =>
        Capabilities.Length == 0 ? "-" : string.Join(", ", Capabilities.OrderBy(item => item));
}

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
        SourceNodeRunId = tableRef.SourceNodeRunId;
        SourceNodeInstanceId = tableRef.SourceNodeInstanceId;
        Role = tableRef.Role;
        StorageKind = tableRef.StorageKind;
        Scope = tableRef.Scope;
        Mutability = tableRef.Mutability;
        ProviderId = tableRef.ProviderId;
        ResourceProfileId = tableRef.ResourceProfileId;
        MountId = tableRef.MountId;
        LogicalTableId = tableRef.LogicalTableId;
        OutputSlot = tableRef.OutputSlot;
        TableType = tableRef.TableType;
        PreviewPersistence = tableRef.PreviewPersistence;
        CanReadRows = tableRef.CanReadRows;
        SupportsPagedRows = tableRef.SupportsPagedRows;
        Version = tableRef.Version;
        Capabilities = tableRef.Capabilities;
        LifecycleStatus = tableRef.LifecycleStatus;
        CreatedAt = tableRef.CreatedAt;
    }

    public string TableRefId { get; }

    public string WorkflowRunId { get; }

    public string NodeRunId { get; }

    public string? SourceNodeRunId { get; }

    public string? SourceNodeInstanceId { get; }

    public string Role { get; }

    public string StorageKind { get; }

    public string Scope { get; }

    public string Mutability { get; }

    public string ProviderId { get; }

    public string? ResourceProfileId { get; }

    public string? MountId { get; }

    public string LogicalTableId { get; }

    public string? OutputSlot { get; }

    public string TableType { get; }

    public string PreviewPersistence { get; }

    public bool CanReadRows { get; }

    public bool SupportsPagedRows { get; }

    public int Version { get; }

    public string[] Capabilities { get; }

    public string LifecycleStatus { get; }

    public DateTimeOffset CreatedAt { get; }

    public string VersionText => $"v{Version}";

    public string CreatedAtText => CreatedAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss");

    public string CapabilitiesText =>
        Capabilities.Length == 0 ? "-" : string.Join(", ", Capabilities.OrderBy(item => item));

    public bool HasCapability(string capability)
    {
        return Capabilities.Any(
            item => string.Equals(item, capability, StringComparison.OrdinalIgnoreCase));
    }
}

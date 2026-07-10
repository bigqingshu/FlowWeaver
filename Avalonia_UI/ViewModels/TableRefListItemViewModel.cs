using System;
using System.Linq;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class TableRefListItemViewModel : ViewModelBase
{
    private readonly Func<string, string> translate;

    public TableRefListItemViewModel(
        TableRefDto tableRef,
        Func<string, string>? translate = null)
    {
        this.translate = translate ?? DefaultText;
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

    public string TableTypeText => translate($"data_preview.table_type.{TableType}");

    public string PreviewPersistenceText =>
        translate($"data_preview.persistence.{PreviewPersistence}");

    public string SourceNodeText => string.IsNullOrWhiteSpace(SourceNodeInstanceId)
        ? NodeRunId
        : SourceNodeInstanceId;

    public string OutputSlotText => string.IsNullOrWhiteSpace(OutputSlot) ? "-" : OutputSlot;

    public string ReadabilityText => CanReadRows
        ? translate("data_preview.readable")
        : $"{translate("data_preview.unreadable")}: {UnreadableReasonText}";

    public string UnreadableReasonText
    {
        get
        {
            if (CanReadRows)
            {
                return string.Empty;
            }

            if (!HasCapability("READ"))
            {
                return translate("data_preview.unreadable.no_read_capability");
            }

            return LifecycleStatus switch
            {
                "RELEASED" => translate("data_preview.unreadable.released"),
                "RETIRED" => translate("data_preview.unreadable.retired"),
                "ORPHANED" => translate("data_preview.unreadable.orphaned"),
                _ => translate("data_preview.unreadable.rows_unavailable"),
            };
        }
    }

    public string DirectorySummaryText =>
        $"{TableTypeText} | {SourceNodeText}.{OutputSlotText} | {StorageKind} | {VersionText} | {PreviewPersistenceText} | {LifecycleStatus} | {ReadabilityText}";

    public bool HasCapability(string capability)
    {
        return Capabilities.Any(
            item => string.Equals(item, capability, StringComparison.OrdinalIgnoreCase));
    }

    public void RefreshLocalizedText()
    {
        OnPropertyChanged(nameof(TableTypeText));
        OnPropertyChanged(nameof(PreviewPersistenceText));
        OnPropertyChanged(nameof(ReadabilityText));
        OnPropertyChanged(nameof(UnreadableReasonText));
        OnPropertyChanged(nameof(DirectorySummaryText));
    }

    private static string DefaultText(string key)
    {
        return key switch
        {
            "data_preview.table_type.current_table" => "Current table",
            "data_preview.table_type.memory_table" => "Memory table",
            "data_preview.table_type.runtime_sql_table" => "Runtime SQL table",
            "data_preview.table_type.external_sql_table" => "External SQL reference",
            "data_preview.persistence.memory_only" => "Temporary memory table",
            "data_preview.persistence.workflow_run_sql" => "Run-persistent table",
            "data_preview.persistence.external_source" => "External SQL source",
            "data_preview.readable" => "Readable",
            "data_preview.unreadable" => "Unreadable",
            "data_preview.unreadable.no_read_capability" => "READ capability is unavailable",
            "data_preview.unreadable.released" => "table was released",
            "data_preview.unreadable.retired" => "table was retired",
            "data_preview.unreadable.orphaned" => "table is orphaned",
            "data_preview.unreadable.rows_unavailable" => "rows are unavailable",
            _ => key,
        };
    }
}

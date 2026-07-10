namespace Avalonia_UI.Models;

public sealed record NodeTableOutputTargetDraft
{
    public const string CurrentTargetKind = "current";
    public const string NewMemoryTargetKind = "new_memory";
    public const string NewRuntimeSqlTargetKind = "new_runtime_sql";
    public const string ExistingMemoryTargetKind = "existing_memory";
    public const string ExistingRuntimeSqlTargetKind = "existing_runtime_sql";

    public string Slot { get; init; } = "out";

    public string TargetKind { get; init; } = CurrentTargetKind;

    public string? LogicalTableId { get; init; }

    public bool IsCurrent => TargetKind == CurrentTargetKind;

    public bool IsNewTarget => TargetKind is
        NewMemoryTargetKind or NewRuntimeSqlTargetKind;

    public bool IsExistingTarget => TargetKind is
        ExistingMemoryTargetKind or ExistingRuntimeSqlTargetKind;

    public bool RequiresLogicalTableId => !IsCurrent;

    public bool IsLogicalTableIdEditable => IsNewTarget;

    public string? StorageKind => TargetKind switch
    {
        NewMemoryTargetKind or ExistingMemoryTargetKind => "MEMORY",
        NewRuntimeSqlTargetKind or ExistingRuntimeSqlTargetKind => "RUNTIME_SQL",
        _ => null,
    };
}

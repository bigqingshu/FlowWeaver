using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Avalonia_UI.Models;

public enum NodeTableBindingsDraftReadStatus
{
    Succeeded,
    JsonInvalid,
    RootNotObject,
    NodesMissing,
    NodeNotFound,
    NodeConfigNotObject,
    BindingInvalid,
    DuplicateSlot,
}

public sealed record NodeTableBindingsDraftReadResult
{
    public NodeTableBindingsDraftReadStatus Status { get; init; }

    public IReadOnlyList<NodeTableInputBindingDraft> InputBindings { get; init; } = [];

    public IReadOnlyList<NodeTableOutputTargetDraft> OutputTargets { get; init; } = [];

    public string? Warning { get; init; }

    public string? ProblemSlot { get; init; }

    public bool Succeeded => Status == NodeTableBindingsDraftReadStatus.Succeeded;
}

public static class NodeTableBindingsDraftReader
{
    private static readonly string[] InputPluralKeys =
        ["input_sources", "input_table_sources"];
    private static readonly string[] OutputPluralKeys =
        ["output_targets", "output_table_targets"];

    public static NodeTableBindingsDraftReadResult Read(
        string workflowDefinitionDraftJson,
        string nodeInstanceId)
    {
        return Read(
            WorkflowDefinitionDraftSnapshot.Parse(workflowDefinitionDraftJson),
            nodeInstanceId);
    }

    public static NodeTableBindingsDraftReadResult Read(
        WorkflowDefinitionDraftSnapshot snapshot,
        string nodeInstanceId)
    {
        if (!snapshot.Succeeded)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.JsonInvalid,
                snapshot.Warning ?? "WORKFLOW_DRAFT_JSON_INVALID");
        }

        var root = snapshot.Root;
        if (root.ValueKind != JsonValueKind.Object)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.RootNotObject,
                "WORKFLOW_DRAFT_ROOT_NOT_OBJECT");
        }

        if (!root.TryGetProperty("nodes", out var nodes) ||
            nodes.ValueKind != JsonValueKind.Array)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.NodesMissing,
                "WORKFLOW_DRAFT_NODES_MISSING");
        }

        JsonElement? selectedNode = null;
        foreach (var node in nodes.EnumerateArray())
        {
            if (node.ValueKind == JsonValueKind.Object &&
                string.Equals(
                    ReadOptionalString(node, "node_instance_id"),
                    nodeInstanceId,
                    StringComparison.Ordinal))
            {
                selectedNode = node;
                break;
            }
        }

        if (selectedNode is null)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.NodeNotFound,
                "NODE_INSTANCE_NOT_FOUND");
        }

        if (!selectedNode.Value.TryGetProperty("config", out var config) ||
            config.ValueKind == JsonValueKind.Null)
        {
            return Succeeded([], []);
        }

        if (config.ValueKind != JsonValueKind.Object)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.NodeConfigNotObject,
                "NODE_CONFIG_NOT_OBJECT");
        }

        var inputs = new List<NodeTableInputBindingDraft>();
        var outputs = new List<NodeTableOutputTargetDraft>();
        var inputSlots = new HashSet<string>(StringComparer.Ordinal);
        var outputSlots = new HashSet<string>(StringComparer.Ordinal);

        if (config.TryGetProperty("input_source", out var singleInput))
        {
            var failure = AddInput(inputs, inputSlots, "in", singleInput);
            if (failure is not null)
            {
                return failure;
            }
        }

        foreach (var key in InputPluralKeys)
        {
            if (!config.TryGetProperty(key, out var value))
            {
                continue;
            }

            var failure = AddInputCollection(inputs, inputSlots, key, value);
            if (failure is not null)
            {
                return failure;
            }
        }

        if (config.TryGetProperty("output_target", out var singleOutput))
        {
            var slot = ReadOptionalString(singleOutput, "slot") ??
                ReadOptionalString(singleOutput, "output_slot") ??
                "out";
            var failure = AddOutput(outputs, outputSlots, slot, singleOutput);
            if (failure is not null)
            {
                return failure;
            }
        }

        foreach (var key in OutputPluralKeys)
        {
            if (!config.TryGetProperty(key, out var value))
            {
                continue;
            }

            var failure = AddOutputCollection(outputs, outputSlots, key, value);
            if (failure is not null)
            {
                return failure;
            }
        }

        if (config.TryGetProperty("output_save", out var outputSave) &&
            outputSave.ValueKind == JsonValueKind.Object &&
            ReadBool(outputSave, "enabled"))
        {
            var slot = ReadOptionalString(outputSave, "slot") ?? "saved_table";
            var failure = AddOutput(
                outputs,
                outputSlots,
                slot,
                outputSave,
                isOutputSave: true);
            if (failure is not null)
            {
                return failure;
            }
        }

        return Succeeded(inputs, outputs);
    }

    private static NodeTableBindingsDraftReadResult? AddInputCollection(
        List<NodeTableInputBindingDraft> inputs,
        HashSet<string> slots,
        string key,
        JsonElement value)
    {
        if (value.ValueKind == JsonValueKind.Object)
        {
            foreach (var property in value.EnumerateObject())
            {
                var failure = AddInput(inputs, slots, property.Name.Trim(), property.Value);
                if (failure is not null)
                {
                    return failure;
                }
            }

            return null;
        }

        if (value.ValueKind != JsonValueKind.Array)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.BindingInvalid,
                $"{key.ToUpperInvariant()}_NOT_COLLECTION");
        }

        var index = 0;
        foreach (var item in value.EnumerateArray())
        {
            var slot = ReadOptionalString(item, "slot") ??
                ReadOptionalString(item, "input_slot");
            if (slot is null)
            {
                return Failed(
                    NodeTableBindingsDraftReadStatus.BindingInvalid,
                    $"{key.ToUpperInvariant()}_{index}_SLOT_REQUIRED");
            }

            var failure = AddInput(inputs, slots, slot, item);
            if (failure is not null)
            {
                return failure;
            }

            index++;
        }

        return null;
    }

    private static NodeTableBindingsDraftReadResult? AddInput(
        List<NodeTableInputBindingDraft> inputs,
        HashSet<string> slots,
        string slot,
        JsonElement value)
    {
        if (string.IsNullOrWhiteSpace(slot) || value.ValueKind != JsonValueKind.Object)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.BindingInvalid,
                "INPUT_SOURCE_INVALID",
                slot);
        }

        if (!slots.Add(slot))
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.DuplicateSlot,
                "DUPLICATE_INPUT_SLOT",
                slot);
        }

        var sourceNodeId = ReadOptionalString(value, "source_node_instance_id");
        var sourceType = NormalizeInputSourceType(
            ReadOptionalString(value, "type"),
            sourceNodeId);
        if (sourceType is null)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.BindingInvalid,
                "INPUT_SOURCE_TYPE_UNSUPPORTED",
                slot);
        }

        if (sourceType == NodeTableInputBindingDraft.UpstreamTableSourceType &&
            sourceNodeId is null)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.BindingInvalid,
                "INPUT_SOURCE_NODE_REQUIRED",
                slot);
        }

        inputs.Add(new NodeTableInputBindingDraft
        {
            Slot = slot,
            Type = sourceType,
            SourceNodeInstanceId = sourceType == NodeTableInputBindingDraft.UpstreamTableSourceType
                ? sourceNodeId
                : null,
            OutputSlot = sourceType == NodeTableInputBindingDraft.UpstreamTableSourceType
                ? ReadOptionalString(value, "output_slot") ??
                    ReadOptionalString(value, "output_alias")
                : null,
            OutputRole = sourceType == NodeTableInputBindingDraft.UpstreamTableSourceType
                ? ReadOptionalString(value, "output_role")
                : null,
            StorageKind = sourceType == NodeTableInputBindingDraft.UpstreamTableSourceType
                ? ReadOptionalString(value, "storage_kind")
                : null,
            LogicalTableId = sourceType == NodeTableInputBindingDraft.UpstreamTableSourceType
                ? ReadOptionalString(value, "logical_table_id")
                : null,
        });
        return null;
    }

    private static NodeTableBindingsDraftReadResult? AddOutputCollection(
        List<NodeTableOutputTargetDraft> outputs,
        HashSet<string> slots,
        string key,
        JsonElement value)
    {
        if (value.ValueKind == JsonValueKind.Object)
        {
            foreach (var property in value.EnumerateObject())
            {
                var failure = AddOutput(outputs, slots, property.Name.Trim(), property.Value);
                if (failure is not null)
                {
                    return failure;
                }
            }

            return null;
        }

        if (value.ValueKind != JsonValueKind.Array)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.BindingInvalid,
                $"{key.ToUpperInvariant()}_NOT_COLLECTION");
        }

        var index = 0;
        foreach (var item in value.EnumerateArray())
        {
            var slot = ReadOptionalString(item, "slot") ??
                ReadOptionalString(item, "output_slot");
            if (slot is null)
            {
                return Failed(
                    NodeTableBindingsDraftReadStatus.BindingInvalid,
                    $"{key.ToUpperInvariant()}_{index}_SLOT_REQUIRED");
            }

            var failure = AddOutput(outputs, slots, slot, item);
            if (failure is not null)
            {
                return failure;
            }

            index++;
        }

        return null;
    }

    private static NodeTableBindingsDraftReadResult? AddOutput(
        List<NodeTableOutputTargetDraft> outputs,
        HashSet<string> slots,
        string slot,
        JsonElement value,
        bool isOutputSave = false)
    {
        if (string.IsNullOrWhiteSpace(slot) || value.ValueKind != JsonValueKind.Object)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.BindingInvalid,
                "OUTPUT_TARGET_INVALID",
                slot);
        }

        if (!slots.Add(slot))
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.DuplicateSlot,
                "DUPLICATE_OUTPUT_SLOT",
                slot);
        }

        var rawTargetKind = ReadOptionalString(value, "target_kind") ??
            ReadOptionalString(value, "target_type");
        var targetKind = isOutputSave
            ? NormalizeOutputSaveTargetKind(rawTargetKind)
            : NormalizeOutputTargetKind(rawTargetKind);
        if (targetKind is null)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.BindingInvalid,
                "OUTPUT_TARGET_KIND_UNSUPPORTED",
                slot);
        }

        var logicalTableId = ReadOptionalString(value, "logical_table_id") ??
            ReadOptionalString(value, "table_name") ??
            ReadOptionalString(value, "target_table");
        if (targetKind == NodeTableOutputTargetDraft.CurrentTargetKind &&
            logicalTableId is not null)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.BindingInvalid,
                "CURRENT_OUTPUT_TARGET_MUST_NOT_BE_NAMED",
                slot);
        }

        if (targetKind != NodeTableOutputTargetDraft.CurrentTargetKind &&
            logicalTableId is null)
        {
            return Failed(
                NodeTableBindingsDraftReadStatus.BindingInvalid,
                "NAMED_OUTPUT_TARGET_REQUIRES_LOGICAL_TABLE_ID",
                slot);
        }

        outputs.Add(new NodeTableOutputTargetDraft
        {
            Slot = slot,
            TargetKind = targetKind,
            LogicalTableId = logicalTableId,
        });
        return null;
    }

    private static string? NormalizeInputSourceType(string? value, string? sourceNodeId)
    {
        return value switch
        {
            null when sourceNodeId is null => NodeTableInputBindingDraft.CurrentSourceType,
            null => NodeTableInputBindingDraft.UpstreamTableSourceType,
            "current" or "current_table" => NodeTableInputBindingDraft.CurrentSourceType,
            "upstream" or "upstream_table" =>
                NodeTableInputBindingDraft.UpstreamTableSourceType,
            _ => null,
        };
    }

    private static string? NormalizeOutputSaveTargetKind(string? value)
    {
        return value switch
        {
            "memory" or "memory_table" or "new_memory" =>
                NodeTableOutputTargetDraft.NewMemoryTargetKind,
            "runtime_sql" or "run_table" or "new_runtime_sql" =>
                NodeTableOutputTargetDraft.NewRuntimeSqlTargetKind,
            _ => null,
        };
    }

    private static string? NormalizeOutputTargetKind(string? value)
    {
        return value switch
        {
            "current" or "current_table" => NodeTableOutputTargetDraft.CurrentTargetKind,
            "memory" or "memory_table" or "new_memory" =>
                NodeTableOutputTargetDraft.NewMemoryTargetKind,
            "runtime_sql" or "run_table" or "new_runtime_sql" =>
                NodeTableOutputTargetDraft.NewRuntimeSqlTargetKind,
            "existing_memory" or "existing_memory_table" =>
                NodeTableOutputTargetDraft.ExistingMemoryTargetKind,
            "existing_runtime_sql" or "existing_run_table" =>
                NodeTableOutputTargetDraft.ExistingRuntimeSqlTargetKind,
            _ => null,
        };
    }

    private static string? ReadOptionalString(JsonElement element, string propertyName)
    {
        if (element.ValueKind != JsonValueKind.Object ||
            !element.TryGetProperty(propertyName, out var property) ||
            property.ValueKind != JsonValueKind.String)
        {
            return null;
        }

        var value = property.GetString()?.Trim();
        return string.IsNullOrEmpty(value) ? null : value;
    }

    private static bool ReadBool(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind is JsonValueKind.True or JsonValueKind.False &&
            property.GetBoolean();
    }

    private static NodeTableBindingsDraftReadResult Succeeded(
        IReadOnlyList<NodeTableInputBindingDraft> inputs,
        IReadOnlyList<NodeTableOutputTargetDraft> outputs)
    {
        return new NodeTableBindingsDraftReadResult
        {
            Status = NodeTableBindingsDraftReadStatus.Succeeded,
            InputBindings = inputs,
            OutputTargets = outputs,
        };
    }

    private static NodeTableBindingsDraftReadResult Failed(
        NodeTableBindingsDraftReadStatus status,
        string warning,
        string? problemSlot = null)
    {
        return new NodeTableBindingsDraftReadResult
        {
            Status = status,
            Warning = warning,
            ProblemSlot = problemSlot,
        };
    }
}

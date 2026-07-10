using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Avalonia_UI.Models;

public enum NodeTableBindingsDraftPatchStatus
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

public sealed record NodeTableBindingsDraftPatchResult
{
    public NodeTableBindingsDraftPatchStatus Status { get; init; }

    public string UpdatedWorkflowDefinitionDraftJson { get; init; } = string.Empty;

    public string? Warning { get; init; }

    public string? ProblemSlot { get; init; }

    public bool Succeeded => Status == NodeTableBindingsDraftPatchStatus.Succeeded;
}

public static class NodeTableBindingsDraftPatcher
{
    private static readonly string[] BindingKeys =
    [
        "input_source",
        "input_sources",
        "input_table_sources",
        "output_target",
        "output_targets",
        "output_table_targets",
        "output_save",
    ];

    private static readonly JsonSerializerOptions IndentedJsonOptions = new()
    {
        WriteIndented = true,
    };

    public static NodeTableBindingsDraftPatchResult Apply(
        string workflowDefinitionDraftJson,
        string nodeInstanceId,
        IReadOnlyList<NodeTableInputBindingDraft> inputBindings,
        IReadOnlyList<NodeTableOutputTargetDraft> outputTargets)
    {
        JsonNode? parsed;
        try
        {
            parsed = JsonNode.Parse(workflowDefinitionDraftJson);
        }
        catch (JsonException)
        {
            return Failed(
                NodeTableBindingsDraftPatchStatus.JsonInvalid,
                "WORKFLOW_DRAFT_JSON_INVALID");
        }

        if (parsed is not JsonObject root)
        {
            return Failed(
                NodeTableBindingsDraftPatchStatus.RootNotObject,
                "WORKFLOW_DRAFT_ROOT_NOT_OBJECT");
        }

        if (root["nodes"] is not JsonArray nodes)
        {
            return Failed(
                NodeTableBindingsDraftPatchStatus.NodesMissing,
                "WORKFLOW_DRAFT_NODES_MISSING");
        }

        var selectedNode = nodes
            .OfType<JsonObject>()
            .FirstOrDefault(node => string.Equals(
                ReadString(node, "node_instance_id"),
                nodeInstanceId,
                StringComparison.Ordinal));
        if (selectedNode is null)
        {
            return Failed(
                NodeTableBindingsDraftPatchStatus.NodeNotFound,
                "NODE_INSTANCE_NOT_FOUND");
        }

        JsonObject config;
        if (!selectedNode.TryGetPropertyValue("config", out var configNode) ||
            configNode is null)
        {
            config = new JsonObject();
            selectedNode["config"] = config;
        }
        else if (configNode is JsonObject configObject)
        {
            config = configObject;
        }
        else
        {
            return Failed(
                NodeTableBindingsDraftPatchStatus.NodeConfigNotObject,
                "NODE_CONFIG_NOT_OBJECT");
        }

        var validation = Validate(inputBindings, outputTargets);
        if (validation is not null)
        {
            return validation;
        }

        foreach (var key in BindingKeys)
        {
            config.Remove(key);
        }

        if (inputBindings.Count > 0)
        {
            var inputs = new JsonObject();
            foreach (var binding in inputBindings.OrderBy(item => item.Slot, StringComparer.Ordinal))
            {
                inputs[binding.Slot] = WriteInput(binding);
            }

            config["input_sources"] = inputs;
        }

        if (outputTargets.Count > 0)
        {
            var outputs = new JsonObject();
            foreach (var target in outputTargets.OrderBy(item => item.Slot, StringComparer.Ordinal))
            {
                outputs[target.Slot] = WriteOutput(target);
            }

            config["output_targets"] = outputs;
        }

        return new NodeTableBindingsDraftPatchResult
        {
            Status = NodeTableBindingsDraftPatchStatus.Succeeded,
            UpdatedWorkflowDefinitionDraftJson = root.ToJsonString(IndentedJsonOptions),
        };
    }

    private static NodeTableBindingsDraftPatchResult? Validate(
        IReadOnlyList<NodeTableInputBindingDraft> inputs,
        IReadOnlyList<NodeTableOutputTargetDraft> outputs)
    {
        var inputSlots = new HashSet<string>(StringComparer.Ordinal);
        foreach (var binding in inputs)
        {
            if (string.IsNullOrWhiteSpace(binding.Slot) ||
                binding.Type is not (
                    NodeTableInputBindingDraft.CurrentSourceType or
                    NodeTableInputBindingDraft.UpstreamTableSourceType))
            {
                return Failed(
                    NodeTableBindingsDraftPatchStatus.BindingInvalid,
                    "INPUT_BINDING_INVALID",
                    binding.Slot);
            }

            if (!inputSlots.Add(binding.Slot))
            {
                return Failed(
                    NodeTableBindingsDraftPatchStatus.DuplicateSlot,
                    "DUPLICATE_INPUT_SLOT",
                    binding.Slot);
            }

            if (binding.IsUpstreamTable &&
                string.IsNullOrWhiteSpace(binding.SourceNodeInstanceId))
            {
                return Failed(
                    NodeTableBindingsDraftPatchStatus.BindingInvalid,
                    "INPUT_SOURCE_NODE_REQUIRED",
                    binding.Slot);
            }
        }

        var outputSlots = new HashSet<string>(StringComparer.Ordinal);
        foreach (var target in outputs)
        {
            if (string.IsNullOrWhiteSpace(target.Slot) || !IsSupportedTargetKind(target.TargetKind))
            {
                return Failed(
                    NodeTableBindingsDraftPatchStatus.BindingInvalid,
                    "OUTPUT_TARGET_INVALID",
                    target.Slot);
            }

            if (!outputSlots.Add(target.Slot))
            {
                return Failed(
                    NodeTableBindingsDraftPatchStatus.DuplicateSlot,
                    "DUPLICATE_OUTPUT_SLOT",
                    target.Slot);
            }

            if (target.IsCurrent && !string.IsNullOrWhiteSpace(target.LogicalTableId))
            {
                return Failed(
                    NodeTableBindingsDraftPatchStatus.BindingInvalid,
                    "CURRENT_OUTPUT_TARGET_MUST_NOT_BE_NAMED",
                    target.Slot);
            }

            if (target.RequiresLogicalTableId &&
                string.IsNullOrWhiteSpace(target.LogicalTableId))
            {
                return Failed(
                    NodeTableBindingsDraftPatchStatus.BindingInvalid,
                    "NAMED_OUTPUT_TARGET_REQUIRES_LOGICAL_TABLE_ID",
                    target.Slot);
            }
        }

        return null;
    }

    private static JsonObject WriteInput(NodeTableInputBindingDraft binding)
    {
        var result = new JsonObject
        {
            ["type"] = binding.Type,
        };
        if (!binding.IsUpstreamTable)
        {
            return result;
        }

        result["source_node_instance_id"] = binding.SourceNodeInstanceId;
        AddOptionalString(result, "output_slot", binding.OutputSlot);
        AddOptionalString(result, "output_role", binding.OutputRole);
        AddOptionalString(result, "storage_kind", binding.StorageKind);
        AddOptionalString(result, "logical_table_id", binding.LogicalTableId);
        return result;
    }

    private static JsonObject WriteOutput(NodeTableOutputTargetDraft target)
    {
        var result = new JsonObject
        {
            ["target_kind"] = target.TargetKind,
        };
        if (!target.IsCurrent)
        {
            result["logical_table_id"] = target.LogicalTableId?.Trim();
        }

        return result;
    }

    private static void AddOptionalString(
        JsonObject target,
        string propertyName,
        string? value)
    {
        if (!string.IsNullOrWhiteSpace(value))
        {
            target[propertyName] = value.Trim();
        }
    }

    private static bool IsSupportedTargetKind(string value)
    {
        return value is
            NodeTableOutputTargetDraft.CurrentTargetKind or
            NodeTableOutputTargetDraft.NewMemoryTargetKind or
            NodeTableOutputTargetDraft.NewRuntimeSqlTargetKind or
            NodeTableOutputTargetDraft.ExistingMemoryTargetKind or
            NodeTableOutputTargetDraft.ExistingRuntimeSqlTargetKind;
    }

    private static string ReadString(JsonObject value, string propertyName)
    {
        return value[propertyName] is JsonValue property &&
            property.TryGetValue<string>(out var text)
                ? text
                : string.Empty;
    }

    private static NodeTableBindingsDraftPatchResult Failed(
        NodeTableBindingsDraftPatchStatus status,
        string warning,
        string? problemSlot = null)
    {
        return new NodeTableBindingsDraftPatchResult
        {
            Status = status,
            Warning = warning,
            ProblemSlot = problemSlot,
        };
    }
}

using System.Text.Json;

namespace Avalonia_UI.Models;

public sealed class WorkflowDefinitionDraftSnapshot
{
    private WorkflowDefinitionDraftSnapshot(
        string draftJson,
        JsonElement root,
        string? warning)
    {
        DraftJson = draftJson;
        Root = root;
        Warning = warning;
    }

    public string DraftJson { get; }

    public JsonElement Root { get; }

    public string? Warning { get; }

    public bool Succeeded => Warning is null;

    public static WorkflowDefinitionDraftSnapshot Parse(string? draftJson)
    {
        var normalizedDraftJson = draftJson ?? string.Empty;
        if (string.IsNullOrWhiteSpace(normalizedDraftJson))
        {
            return new WorkflowDefinitionDraftSnapshot(
                normalizedDraftJson,
                default,
                "WORKFLOW_DRAFT_JSON_INVALID");
        }

        try
        {
            using var document = JsonDocument.Parse(normalizedDraftJson);
            return new WorkflowDefinitionDraftSnapshot(
                normalizedDraftJson,
                document.RootElement.Clone(),
                warning: null);
        }
        catch (JsonException)
        {
            return new WorkflowDefinitionDraftSnapshot(
                normalizedDraftJson,
                default,
                "WORKFLOW_DRAFT_JSON_INVALID");
        }
    }
}

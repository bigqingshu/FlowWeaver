namespace Avalonia_UI.Models;

public enum NodeConfigDraftApplyStatus
{
    Succeeded,
    JsonInvalid,
    NodesMissing,
    NodeNotFound,
    NodeConfigNotObject,
    ConfigUnsupported,
    PatchConflict,
}

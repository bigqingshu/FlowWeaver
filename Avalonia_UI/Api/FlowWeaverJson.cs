using System.Text.Json;

namespace Avalonia_UI.Api;

public static class FlowWeaverJson
{
    public static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web)
    {
        PropertyNameCaseInsensitive = true,
    };
}

using PKHeX.Core;

if (args.Length != 5)
{
    Console.Error.WriteLine("usage: SaveIdentityTool INPUT OUTPUT OT TID16 SID16");
    return 2;
}

var input = args[0];
var output = args[1];
var ot = args[2];
if (!ushort.TryParse(args[3], out var tid) || !ushort.TryParse(args[4], out var sid))
    throw new ArgumentException("TID16 and SID16 must be unsigned 16-bit integers.");

var save = SaveUtil.GetSaveFile(input) ?? throw new InvalidDataException("Save was not recognized.");
if (save is not SAV9SV)
    throw new InvalidDataException($"Expected a Scarlet/Violet save, got {save.GetType().Name}.");

Console.WriteLine($"OLD OT={save.OT} TID16={save.TID16} SID16={save.SID16}");
save.OT = ot;
save.TID16 = tid;
save.SID16 = sid;
File.WriteAllBytes(output, save.Write().ToArray());
Console.WriteLine($"NEW OT={save.OT} TID16={save.TID16} SID16={save.SID16} BYTES={new FileInfo(output).Length}");
return 0;
